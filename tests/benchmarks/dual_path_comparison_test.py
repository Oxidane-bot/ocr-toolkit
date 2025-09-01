"""
True dual-path comparison test: MarkItDown vs PDF-conversion-then-OCR.

This script provides a fair comparison by processing all documents through both pipelines:
- Path A: MarkItDown direct processing of original files
- Path B: Convert to PDF first, then OCR processing

Both paths process the same content, providing a true end-to-end comparison.
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit import common, config
from markitdown import MarkItDown
from office_to_pdf_converter import convert_office_to_pdf, setup_logging as setup_converter_logging


def setup_logging(log_dir: str) -> None:
    """Configure logging for the comparison test."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"dual_path_test_{int(time.time())}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging to: {log_file}")


def discover_all_files(input_path: str) -> List[str]:
    """
    Discover all supported files in the given path.
    
    Args:
        input_path: Path to file or directory
        
    Returns:
        List of file paths to process
    """
    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.ppt', '.doc', '.xls'}
    files = []
    
    if os.path.isfile(input_path):
        if Path(input_path).suffix.lower() in supported_extensions:
            files.append(input_path)
    elif os.path.isdir(input_path):
        for filename in sorted(os.listdir(input_path)):
            filepath = os.path.join(input_path, filename)
            if os.path.isfile(filepath) and Path(filepath).suffix.lower() in supported_extensions:
                files.append(filepath)
    
    return files


def process_path_a_markitdown(file_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Path A: Process file directly with MarkItDown.
    
    Args:
        file_path: Path to input file
        output_dir: Directory for output files
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'path': 'A_markitdown_direct',
        'file_path': file_path,
        'success': False,
        'total_processing_time': 0,
        'markitdown_time': 0,
        'conversion_time': 0,  # N/A for direct processing
        'output_file': '',
        'output_size': 0,
        'text_length': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        # Process directly with MarkItDown
        md_start = time.time()
        md = MarkItDown()
        markdown_result = md.convert(file_path)
        markdown_text = markdown_result.text_content
        result['markitdown_time'] = time.time() - md_start
        
        # Save output
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}_pathA_markitdown.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        # Update result
        result['success'] = True
        result['output_file'] = output_file
        result['output_size'] = os.path.getsize(output_file)
        result['text_length'] = len(markdown_text)
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Path A (MarkItDown direct) failed for {file_path}: {e}")
        logging.debug(traceback.format_exc())
    
    result['total_processing_time'] = time.time() - start_time
    return result


def process_path_b_convert_then_ocr(file_path: str, output_dir: str, temp_dir: str,
                                   det_arch: str, reco_arch: str, batch_size: int, 
                                   use_cpu: bool, ocr_model) -> Dict[str, Any]:
    """
    Path B: Convert to PDF first, then process with OCR.
    
    Args:
        file_path: Path to input file
        output_dir: Directory for output files
        temp_dir: Directory for temporary PDF files
        det_arch: Detection architecture for OCR
        reco_arch: Recognition architecture for OCR
        batch_size: Batch size for OCR processing
        use_cpu: Whether to force CPU usage for OCR
        ocr_model: Pre-loaded OCR model (for efficiency)
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'path': 'B_convert_then_ocr',
        'file_path': file_path,
        'success': False,
        'total_processing_time': 0,
        'conversion_time': 0,
        'ocr_time': 0,
        'output_file': '',
        'output_size': 0,
        'text_length': 0,
        'pages_processed': 0,
        'temp_pdf_file': '',
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        # Step 1: Convert to PDF
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        temp_pdf_path = os.path.join(temp_dir, f"{base_name}_temp.pdf")
        
        conversion_result = convert_office_to_pdf(file_path, temp_pdf_path)
        result['conversion_time'] = conversion_result['processing_time']
        result['temp_pdf_file'] = temp_pdf_path
        
        if not conversion_result['success']:
            result['error'] = f"PDF conversion failed: {conversion_result['error']}"
            result['total_processing_time'] = time.time() - start_time
            return result
        
        # Step 2: Process PDF with OCR
        try:
            from doctr.io import DocumentFile
            
            ocr_start = time.time()
            
            # Load PDF
            doc = DocumentFile.from_pdf(temp_pdf_path)
            logging.info(f"Path B: Loaded PDF with {len(doc)} pages")
            
            # Process in batches
            markdown_content = []
            num_batches = (len(doc) + batch_size - 1) // batch_size
            
            for i in range(0, len(doc), batch_size):
                batch = doc[i : i + batch_size]
                batch_result = ocr_model(batch)
                
                for page_idx, page_result in enumerate(batch_result.pages):
                    current_page_number = i + page_idx + 1
                    text = page_result.render()
                    markdown_content.append(f"## Page {current_page_number}\n\n{text}")
            
            # Combine all pages
            markdown_text = "\n\n".join(markdown_content)
            result['ocr_time'] = time.time() - ocr_start
            result['pages_processed'] = len(doc)
            
            # Save output
            output_file = os.path.join(output_dir, f"{base_name}_pathB_convert_ocr.md")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            # Update result
            result['success'] = True
            result['output_file'] = output_file
            result['output_size'] = os.path.getsize(output_file)
            result['text_length'] = len(markdown_text)
            
        except Exception as e:
            result['error'] = f"OCR processing failed: {str(e)}"
            logging.error(f"OCR processing failed for {temp_pdf_path}: {e}")
        
        # Clean up temporary PDF file
        try:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except:
            pass  # Don't fail the whole process if cleanup fails
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Path B (convert then OCR) failed for {file_path}: {e}")
        logging.debug(traceback.format_exc())
    
    result['total_processing_time'] = time.time() - start_time
    return result


def run_dual_path_comparison(input_path: str, pathA_output_dir: str, pathB_output_dir: str,
                           temp_dir: str, reports_dir: str, det_arch: str, reco_arch: str,
                           batch_size: int, use_cpu: bool) -> Dict[str, Any]:
    """
    Run dual-path comparison tests on all files.
    
    Args:
        input_path: Path to input file(s)
        pathA_output_dir: Directory for Path A outputs
        pathB_output_dir: Directory for Path B outputs
        temp_dir: Directory for temporary files
        reports_dir: Directory for reports
        det_arch: Detection architecture for OCR
        reco_arch: Recognition architecture for OCR
        batch_size: Batch size for OCR processing
        use_cpu: Whether to force CPU usage for OCR
        
    Returns:
        Dictionary containing all test results
    """
    # Setup directories
    for dir_path in [pathA_output_dir, pathB_output_dir, temp_dir, reports_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Discover files to process
    files_to_process = discover_all_files(input_path)
    if not files_to_process:
        logging.error("No supported files found to process")
        return {}
    
    logging.info(f"Found {len(files_to_process)} files to process")
    
    # Load OCR model once (for efficiency in Path B)
    logging.info("Loading OCR model for Path B processing...")
    ocr_model = common.load_ocr_model(det_arch, reco_arch, use_cpu)
    
    # Initialize results storage
    comparison_results = {
        'test_timestamp': int(time.time()),
        'test_type': 'dual_path_comparison',
        'input_path': input_path,
        'total_files': len(files_to_process),
        'ocr_settings': {
            'det_arch': det_arch,
            'reco_arch': reco_arch,
            'batch_size': batch_size,
            'use_cpu': use_cpu
        },
        'results': []
    }
    
    # Process each file with both paths
    for i, file_path in enumerate(files_to_process, 1):
        logging.info(f"\n=== Processing file {i}/{len(files_to_process)}: {os.path.basename(file_path)} ===")
        
        file_result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': os.path.getsize(file_path),
            'file_extension': Path(file_path).suffix.lower(),
            'path_a_result': None,
            'path_b_result': None
        }
        
        # Process with Path A (MarkItDown direct)
        logging.info("Path A: Processing with MarkItDown (direct)...")
        file_result['path_a_result'] = process_path_a_markitdown(
            file_path, pathA_output_dir
        )
        
        # Process with Path B (convert to PDF then OCR)
        logging.info("Path B: Converting to PDF then OCR...")
        file_result['path_b_result'] = process_path_b_convert_then_ocr(
            file_path, pathB_output_dir, temp_dir, det_arch, reco_arch, 
            batch_size, use_cpu, ocr_model
        )
        
        comparison_results['results'].append(file_result)
        
        # Log summary for this file
        path_a_success = file_result['path_a_result']['success']
        path_b_success = file_result['path_b_result']['success']
        path_a_time = file_result['path_a_result']['total_processing_time']
        path_b_time = file_result['path_b_result']['total_processing_time']
        
        logging.info(f"Results: Path A={'✓' if path_a_success else '✗'} ({path_a_time:.2f}s), " +
                    f"Path B={'✓' if path_b_success else '✗'} ({path_b_time:.2f}s)")
    
    # Save detailed results
    report_file = os.path.join(reports_dir, f"dual_path_results_{comparison_results['test_timestamp']}.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    logging.info(f"\nDetailed results saved to: {report_file}")
    return comparison_results


def print_summary(results: Dict[str, Any]) -> None:
    """Print a summary of the dual-path comparison results."""
    if not results or not results.get('results'):
        logging.info("No results to summarize")
        return
    
    total_files = results['total_files']
    
    # Calculate success rates
    path_a_successes = sum(1 for r in results['results'] if r['path_a_result']['success'])
    path_b_successes = sum(1 for r in results['results'] if r['path_b_result']['success'])
    
    # Calculate total times
    path_a_total_time = sum(r['path_a_result']['total_processing_time'] 
                           for r in results['results'] if r['path_a_result']['success'])
    path_b_total_time = sum(r['path_b_result']['total_processing_time'] 
                           for r in results['results'] if r['path_b_result']['success'])
    
    # Calculate conversion vs OCR time breakdown for Path B
    path_b_conversion_time = sum(r['path_b_result']['conversion_time'] 
                               for r in results['results'] if r['path_b_result']['success'])
    path_b_ocr_time = sum(r['path_b_result']['ocr_time'] 
                         for r in results['results'] if r['path_b_result']['success'])
    
    logging.info("\n" + "="*80)
    logging.info("DUAL-PATH COMPARISON SUMMARY")
    logging.info("="*80)
    logging.info(f"Total files processed: {total_files}")
    logging.info(f"")
    logging.info(f"PATH A (MarkItDown Direct):")
    logging.info(f"  Success rate: {path_a_successes}/{total_files} ({path_a_successes/total_files*100:.1f}%)")
    logging.info(f"  Total processing time: {path_a_total_time:.2f}s")
    if path_a_successes > 0:
        logging.info(f"  Average time per file: {path_a_total_time/path_a_successes:.2f}s")
    
    logging.info(f"")
    logging.info(f"PATH B (Convert to PDF → OCR):")
    logging.info(f"  Success rate: {path_b_successes}/{total_files} ({path_b_successes/total_files*100:.1f}%)")
    logging.info(f"  Total processing time: {path_b_total_time:.2f}s")
    logging.info(f"    - PDF conversion time: {path_b_conversion_time:.2f}s")
    logging.info(f"    - OCR processing time: {path_b_ocr_time:.2f}s")
    if path_b_successes > 0:
        logging.info(f"  Average time per file: {path_b_total_time/path_b_successes:.2f}s")
    
    logging.info(f"")
    if path_a_successes > 0 and path_b_successes > 0:
        speed_ratio = (path_b_total_time/path_b_successes) / (path_a_total_time/path_a_successes)
        logging.info(f"Speed comparison: Path B is {speed_ratio:.1f}x slower than Path A")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the dual-path comparison test."""
    parser = argparse.ArgumentParser(
        description="Dual-path comparison: MarkItDown vs PDF-conversion-then-OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input_path',
        help='Path to file or directory containing documents to process'
    )
    
    parser.add_argument(
        '--results-dir',
        default='comparison_tests/results_dual_path',
        help='Base directory for all results (default: comparison_tests/results_dual_path)'
    )
    
    # Add common OCR arguments
    common.add_common_args(parser)
    
    return parser


def main():
    """Main entry point for the dual-path comparison test."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up directories
    base_results_dir = args.results_dir
    pathA_output_dir = os.path.join(base_results_dir, 'path_a_markitdown_direct')
    pathB_output_dir = os.path.join(base_results_dir, 'path_b_convert_then_ocr')
    temp_dir = os.path.join(base_results_dir, 'temp_pdfs')
    reports_dir = os.path.join(base_results_dir, 'reports')
    logs_dir = os.path.join(os.path.dirname(base_results_dir), 'logs')
    
    # Set up logging
    setup_logging(logs_dir)
    
    logging.info("Starting dual-path comparison test")
    logging.info(f"Input path: {args.input_path}")
    logging.info(f"Results will be saved to: {base_results_dir}")
    logging.info("Path A: MarkItDown direct processing")
    logging.info("Path B: Convert to PDF → OCR processing")
    
    try:
        # Run dual-path comparison
        results = run_dual_path_comparison(
            args.input_path,
            pathA_output_dir,
            pathB_output_dir,
            temp_dir,
            reports_dir,
            args.det_arch,
            args.reco_arch,
            args.batch_size,
            args.cpu
        )
        
        # Print summary
        print_summary(results)
        
        logging.info("Dual-path comparison test completed successfully!")
        
    except KeyboardInterrupt:
        logging.info("Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Test failed with error: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up temp directory
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logging.info("Cleaned up temporary files")
        except:
            pass


if __name__ == "__main__":
    main()