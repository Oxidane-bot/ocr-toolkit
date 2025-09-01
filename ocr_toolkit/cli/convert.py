"""
CLI for document conversion using MarkItDown.

This module provides a command-line interface for converting various document
formats to Markdown using MarkItDown, optimized for high performance and ease of use.
"""

# Suppress pypdf warnings at the very beginning
import logging
import warnings
import os
import argparse
import sys
from pathlib import Path

from .. import config
from ..utils import discover_files, load_ocr_model, get_output_file_path, add_common_ocr_args



def setup_logging():
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def create_parser():
    """Create argument parser for convert command."""
    parser = argparse.ArgumentParser(
        description="Convert documents to Markdown using MarkItDown",
        prog="ocr-convert",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single document
  ocr-convert document.docx
  
  # Convert all documents in directory
  ocr-convert /path/to/documents/
  
  # Specify output directory
  ocr-convert documents/ --output-dir markdown_files/
  
  # Use multiple workers for faster processing
  ocr-convert documents/ --workers 8
  
  # List supported formats
  ocr-convert --list-formats

Supported formats:
  Office: .docx, .pptx, .xlsx, .doc, .ppt, .xls
  PDF: .pdf
  Text: .txt, .md, .html, .htm, .rtf
  OpenDocument: .odt, .odp, .ods
  Data: .csv, .tsv, .json, .xml
  E-books: .epub
        """
    )
    
    parser.add_argument(
        "input_path", 
        nargs='?',
        help="Path to document file or directory containing documents"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Output directory for Markdown files (default: '{config.DEFAULT_MARKDOWN_OUTPUT_DIR}' in input directory)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers for batch processing (default: 4)"
    )
    
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List supported file formats and exit"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Increase output verbosity"
    )
    
    # Add common OCR arguments
    add_common_ocr_args(parser)
    
    return parser


def list_supported_formats():
    """Display supported file formats."""
    from ..config import get_all_supported_formats
    
    print("Supported file formats:")
    print("=====================")
    
    # Get all supported formats from centralized config
    all_supported = get_all_supported_formats()
    
    categories = {
        "Office Documents": ['.docx', '.pptx', '.xlsx', '.doc', '.ppt', '.xls'],
        "PDF Documents": ['.pdf'],
        "Image Files": ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'],
        "Text Documents": ['.txt', '.md', '.html', '.htm', '.rtf'],
        "OpenDocument": ['.odt', '.odp', '.ods'],
        "Data Files": ['.csv', '.tsv', '.json', '.xml'],
        "E-books": ['.epub']
    }
    
    for category, exts in categories.items():
        available_formats = [ext for ext in exts if ext in all_supported]
        if available_formats:
            print(f"\n{category}:")
            print(f"  {', '.join(available_formats)}")
    
    print(f"\nTotal supported formats: {len(all_supported)}")


def validate_arguments(args):
    """Validate command line arguments."""
    if args.list_formats:
        return True  # No need to validate input_path for --list-formats
    
    if not args.input_path:
        print("Error: input_path is required (unless using --list-formats)")
        return False
    
    if args.workers < 1:
        print("Error: --workers must be at least 1")
        return False
    
    if args.workers > 16:
        print("Warning: Using more than 16 workers may not improve performance")
    
    return True


def main():
    """Main entry point for ocr-convert command."""
    import warnings
    # Suppress verbose warnings from the pypdf library
    warnings.filterwarnings("ignore", message="Cannot set non-stroke color because 2 components are specified but only 1 (grayscale), 3 (rgb) and 4 (cmyk) are supported", module="pypdf")
    warnings.filterwarnings("ignore", message="Could get FontBBox from font descriptor because None cannot be parsed as 4 floats", module="pypdf")

    from .. import dual_processor
    from argparse import Namespace

    parser = create_parser()
    args = parser.parse_args()
    
    # Handle --list-formats
    if args.list_formats:
        list_supported_formats()
        return
    
    # Validate arguments
    if not validate_arguments(args):
        parser.print_help()
        sys.exit(1)
    
    # Configure logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    setup_logging()
    
    try:
        # Validate input path
        if not os.path.exists(args.input_path):
            logging.error(f"Input path does not exist: {args.input_path}")
            sys.exit(1)
        
        # Discover files to process
        files_to_process, _ = discover_files(args.input_path)

        if not files_to_process:
            logging.info("No supported files found to process.")
            sys.exit(0)
        
        # Display initial information
        logging.info(f"Converting {len(files_to_process)} files from: {args.input_path}")
        if args.output_dir:
            logging.info(f"Output directory: {args.output_dir}")
        
        # Prepare OCR arguments, using passed args or falling back to defaults
        ocr_args = Namespace(
            det_arch=args.det_arch or config.DEFAULT_DET_ARCH,
            reco_arch=args.reco_arch or config.DEFAULT_RECO_ARCH,
            batch_size=args.batch_size,
            cpu=args.cpu
        )
        
        # Load OCR model
        logging.info(f"Loading OCR model (det_arch={ocr_args.det_arch}, reco_arch={ocr_args.reco_arch})...")
        ocr_model = load_ocr_model(ocr_args.det_arch, ocr_args.reco_arch, ocr_args.cpu)
        
        # Create dual processor
        processor = dual_processor.DualProcessor(ocr_model)
        
        # Process documents
        results = []
        for file_path in files_to_process:
            logging.info(f"Processing {file_path}...")
            result = processor.process_document_dual(file_path, ocr_args)
            results.append(result)
            
            # Save the result
            output_file_path = get_output_file_path(file_path, args.output_dir)
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(result['final_content'])
            
            status = "SUCCESS" if result['success'] else "FAILED"
            method = result['chosen_method']
            logging.info(f"  -> {status} (Method: {method})")
        
        # Display results summary
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)
        
        total_files = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total_files - successful
        success_rate = (successful / total_files * 100) if total_files > 0 else 0
        
        print(f"Total files processed: {total_files}")
        print(f"Successful conversions: {successful}")
        print(f"Failed conversions: {failed}")
        print(f"Success rate: {success_rate:.1f}%")
        
        # Get dual processing statistics
        stats = processor.get_statistics()
        print(f"\nMethod Selection:")
        print(f"  MarkItDown chosen: {stats['markitdown_chosen']} ({stats['markitdown_chosen_pct']:.1f}%)")
        print(f"  OCR chosen: {stats['ocr_chosen']} ({stats['ocr_chosen_pct']:.1f}%)")
        
        # Determine output directory
        output_directory = args.output_dir if args.output_dir else os.path.join(args.input_path, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        print(f"Output directory: {output_directory}")
        
        # List failed files if any
        if failed > 0:
            print(f"\nFailed files:")
            for file_result in results:
                if not file_result['success']:
                    error = file_result.get('error', 'Unknown error')
                    print(f"  - {file_result['file_name']}: {error}")
        
        print(f"\nConversion completed! Files saved to: {output_directory}")
        
        # Exit with error code if any files failed
        if failed > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        logging.info("Conversion cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()