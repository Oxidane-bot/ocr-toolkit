"""
Comparison testing script for OCR vs MarkItDown approaches.

This script processes documents using both the existing OCR pipeline 
and MarkItDown to compare their effectiveness on various file formats.
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit import common, config
from markitdown import MarkItDown


def setup_logging(log_dir: str) -> None:
    """Configure logging for the comparison test."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"comparison_test_{int(time.time())}.log")
    
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


def process_with_ocr(file_path: str, output_dir: str, det_arch: str, reco_arch: str, 
                    batch_size: int, use_cpu: bool) -> Dict[str, Any]:
    """
    Process file using OCR pipeline (converts to PDF first if needed).
    
    Args:
        file_path: Path to input file
        output_dir: Directory for output files
        det_arch: Detection architecture
        reco_arch: Recognition architecture  
        batch_size: Batch size for processing
        use_cpu: Whether to force CPU usage
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'method': 'ocr',
        'file_path': file_path,
        'success': False,
        'processing_time': 0,
        'output_file': '',
        'output_size': 0,
        'text_length': 0,
        'pages_processed': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        # For non-PDF files, we'd need to convert them first
        # This is a limitation of the current OCR pipeline
        if not file_path.lower().endswith('.pdf'):
            result['error'] = 'OCR pipeline only supports PDF files directly'
            result['processing_time'] = time.time() - start_time
            return result
        
        # Import OCR dependencies
        from doctr.io import DocumentFile
        
        # Load OCR model (only once per batch would be more efficient)
        model = common.load_ocr_model(det_arch, reco_arch, use_cpu)
        
        # Load PDF
        doc = DocumentFile.from_pdf(file_path)
        logging.info(f"OCR: Loaded PDF with {len(doc)} pages")
        
        # Process in batches
        markdown_content = []
        num_batches = (len(doc) + batch_size - 1) // batch_size
        
        for i in range(0, len(doc), batch_size):
            batch = doc[i : i + batch_size]
            batch_result = model(batch)
            
            for page_idx, page_result in enumerate(batch_result.pages):
                current_page_number = i + page_idx + 1
                text = page_result.render()
                markdown_content.append(f"## Page {current_page_number}\n\n{text}")
        
        # Combine all pages
        markdown_text = "\n\n".join(markdown_content)
        
        # Save output
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}_ocr.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        # Update result
        result['success'] = True
        result['output_file'] = output_file
        result['output_size'] = os.path.getsize(output_file)
        result['text_length'] = len(markdown_text)
        result['pages_processed'] = len(doc)
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"OCR processing failed for {file_path}: {e}")
        logging.debug(traceback.format_exc())
    
    result['processing_time'] = time.time() - start_time
    return result


def process_with_markitdown(file_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Process file using MarkItDown.
    
    Args:
        file_path: Path to input file
        output_dir: Directory for output files
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'method': 'markitdown',
        'file_path': file_path,
        'success': False,
        'processing_time': 0,
        'output_file': '',
        'output_size': 0,
        'text_length': 0,
        'pages_processed': 0,  # MarkItDown doesn't track pages the same way
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        # Initialize MarkItDown
        md = MarkItDown()
        
        # Process the file
        markdown_result = md.convert(file_path)
        markdown_text = markdown_result.text_content
        
        # Save output
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}_markitdown.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        # Update result
        result['success'] = True
        result['output_file'] = output_file
        result['output_size'] = os.path.getsize(output_file)
        result['text_length'] = len(markdown_text)
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"MarkItDown processing failed for {file_path}: {e}")
        logging.debug(traceback.format_exc())
    
    result['processing_time'] = time.time() - start_time
    return result


def run_comparison_tests(input_path: str, ocr_output_dir: str, markitdown_output_dir: str,
                        reports_dir: str, det_arch: str, reco_arch: str, 
                        batch_size: int, use_cpu: bool) -> Dict[str, Any]:
    """
    Run comparison tests on all files in the input path.
    
    Args:
        input_path: Path to input file(s)
        ocr_output_dir: Directory for OCR outputs
        markitdown_output_dir: Directory for MarkItDown outputs
        reports_dir: Directory for reports
        det_arch: Detection architecture for OCR
        reco_arch: Recognition architecture for OCR
        batch_size: Batch size for OCR processing
        use_cpu: Whether to force CPU usage for OCR
        
    Returns:
        Dictionary containing all test results
    """
    # Ensure output directories exist
    os.makedirs(ocr_output_dir, exist_ok=True)
    os.makedirs(markitdown_output_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # Discover files to process
    files_to_process = discover_all_files(input_path)
    if not files_to_process:
        logging.error("No supported files found to process")
        return {}
    
    logging.info(f"Found {len(files_to_process)} files to process")
    
    # Initialize results storage
    comparison_results = {
        'test_timestamp': int(time.time()),
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
    
    # Process each file with both methods
    for i, file_path in enumerate(files_to_process, 1):
        logging.info(f"\n=== Processing file {i}/{len(files_to_process)}: {os.path.basename(file_path)} ===")
        
        file_result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': os.path.getsize(file_path),
            'file_extension': Path(file_path).suffix.lower(),
            'ocr_result': None,
            'markitdown_result': None
        }
        
        # Process with OCR
        logging.info("Processing with OCR pipeline...")
        file_result['ocr_result'] = process_with_ocr(
            file_path, ocr_output_dir, det_arch, reco_arch, batch_size, use_cpu
        )
        
        # Process with MarkItDown
        logging.info("Processing with MarkItDown...")
        file_result['markitdown_result'] = process_with_markitdown(
            file_path, markitdown_output_dir
        )
        
        comparison_results['results'].append(file_result)
        
        # Log summary for this file
        ocr_success = file_result['ocr_result']['success']
        md_success = file_result['markitdown_result']['success']
        logging.info(f"Results: OCR={'✓' if ocr_success else '✗'}, MarkItDown={'✓' if md_success else '✗'}")
    
    # Save detailed results
    report_file = os.path.join(reports_dir, f"comparison_results_{comparison_results['test_timestamp']}.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    logging.info(f"\nDetailed results saved to: {report_file}")
    return comparison_results


def print_summary(results: Dict[str, Any]) -> None:
    """Print a summary of the comparison results."""
    if not results or not results.get('results'):
        logging.info("No results to summarize")
        return
    
    total_files = results['total_files']
    ocr_successes = sum(1 for r in results['results'] if r['ocr_result']['success'])
    md_successes = sum(1 for r in results['results'] if r['markitdown_result']['success'])
    
    ocr_total_time = sum(r['ocr_result']['processing_time'] for r in results['results'] 
                        if r['ocr_result']['success'])
    md_total_time = sum(r['markitdown_result']['processing_time'] for r in results['results'] 
                       if r['markitdown_result']['success'])
    
    logging.info("\n" + "="*60)
    logging.info("COMPARISON SUMMARY")
    logging.info("="*60)
    logging.info(f"Total files processed: {total_files}")
    logging.info(f"OCR success rate: {ocr_successes}/{total_files} ({ocr_successes/total_files*100:.1f}%)")
    logging.info(f"MarkItDown success rate: {md_successes}/{total_files} ({md_successes/total_files*100:.1f}%)")
    logging.info(f"OCR total processing time: {ocr_total_time:.2f}s")
    logging.info(f"MarkItDown total processing time: {md_total_time:.2f}s")
    
    if ocr_successes > 0:
        logging.info(f"OCR average time per file: {ocr_total_time/ocr_successes:.2f}s")
    if md_successes > 0:
        logging.info(f"MarkItDown average time per file: {md_total_time/md_successes:.2f}s")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the comparison test."""
    parser = argparse.ArgumentParser(
        description="Compare OCR and MarkItDown processing on document files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input_path',
        help='Path to file or directory containing documents to process'
    )
    
    parser.add_argument(
        '--results-dir',
        default='comparison_tests/results',
        help='Base directory for all results (default: comparison_tests/results)'
    )
    
    # Add common OCR arguments
    common.add_common_args(parser)
    
    return parser


def main():
    """Main entry point for the comparison test."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up directories
    base_results_dir = args.results_dir
    ocr_output_dir = os.path.join(base_results_dir, 'ocr_outputs')
    markitdown_output_dir = os.path.join(base_results_dir, 'markitdown_outputs')
    reports_dir = os.path.join(base_results_dir, 'reports')
    logs_dir = os.path.join(os.path.dirname(base_results_dir), 'logs')
    
    # Set up logging
    setup_logging(logs_dir)
    
    logging.info("Starting OCR vs MarkItDown comparison test")
    logging.info(f"Input path: {args.input_path}")
    logging.info(f"Results will be saved to: {base_results_dir}")
    
    try:
        # Run comparison tests
        results = run_comparison_tests(
            args.input_path,
            ocr_output_dir,
            markitdown_output_dir,
            reports_dir,
            args.det_arch,
            args.reco_arch,
            args.batch_size,
            args.cpu
        )
        
        # Print summary
        print_summary(results)
        
        logging.info("Comparison test completed successfully!")
        
    except KeyboardInterrupt:
        logging.info("Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Test failed with error: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()