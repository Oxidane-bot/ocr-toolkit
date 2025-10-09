"""
CLI for document conversion using MarkItDown.

This module provides a command-line interface for converting various document
formats to Markdown using MarkItDown, optimized for high performance and ease of use.
"""

# Suppress pypdf warnings at the very beginning
import logging
import os
import sys
import time
import warnings
from argparse import Namespace

import torch

from .. import config
from .. import ocr_processor_wrapper
from ..utils import (
    BaseArgumentParser,
    add_common_ocr_args,
    add_output_args,
    check_input_path_exists,
    configure_logging_level,
    discover_files,
    generate_file_tree,
    get_directory_cache,
    get_output_file_path,
    load_ocr_model,
    setup_logging,
    validate_common_arguments,
)


def create_parser():
    """Create argument parser for convert command."""
    epilog = """
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

    parser = BaseArgumentParser.create_base_parser(
        prog="ocr-convert",
        description="Convert documents to Markdown using advanced OCR",
        epilog=epilog
    )

    BaseArgumentParser.add_input_path_argument(
        parser,
        required=False,
        help="Path to document file or directory containing documents"
    )

    BaseArgumentParser.add_workers_argument(parser, default=4)

    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List supported file formats and exit"
    )

    # Add common output arguments (includes preserve-structure, no-recursive)
    add_output_args(parser)

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

    # Use common validation
    return validate_common_arguments(args)


def main():
    """Main entry point for ocr-convert command."""
    # Suppress verbose warnings from the pypdf library
    warnings.filterwarnings("ignore", message="Cannot set non-stroke color because 2 components are specified but only 1 (grayscale), 3 (rgb) and 4 (cmyk) are supported", module="pypdf")
    warnings.filterwarnings("ignore", message="Could get FontBBox from font descriptor because None cannot be parsed as 4 floats", module="pypdf")

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

    # Configure logging
    setup_logging()
    configure_logging_level(args)

    try:
        # Record start time for performance monitoring
        conversion_start_time = time.time()

        # Validate input path
        if not check_input_path_exists(args):
            sys.exit(1)

        # Discover files to process
        recursive = not args.no_recursive
        files_to_process, base_dir, file_relative_paths = discover_files(args.input_path, recursive=recursive)

        if not files_to_process:
            logging.info("No supported files found to process.")
            sys.exit(0)

        # Display initial information
        search_type = "recursively" if recursive else "non-recursively"
        logging.info(f"Searching {search_type} - found {len(files_to_process)} files from: {args.input_path}")
        if args.preserve_structure:
            logging.info("Directory structure will be preserved in output")
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
        logging.info(f"CPU flag: {ocr_args.cpu}, CUDA available: {torch.cuda.is_available()}")
        ocr_model = load_ocr_model(ocr_args.det_arch, ocr_args.reco_arch, ocr_args.cpu)

        # Create OCR processor wrapper (replaces legacy dual_processor)
        processor = ocr_processor_wrapper.create_ocr_processor_wrapper(
            ocr_model,
            batch_size=ocr_args.batch_size,
            use_zh=getattr(args, 'zh', False)
        )

        # Get directory cache for optimized directory creation
        dir_cache = get_directory_cache()
        dir_cache.reset()  # Reset cache for this conversion session

        # Display output directory structure preview for preserve structure mode
        if args.preserve_structure and len(files_to_process) > 1:
            # Determine output directory for preview - must match get_output_file_path logic
            if args.output_dir:
                output_directory = args.output_dir
            else:
                # For preserve structure mode, use input base directory
                output_directory = os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)

            logging.info("Directory structure preview:")
            logging.info(f"  Input base: {base_dir}")
            logging.info(f"  Output base: {output_directory}")
            logging.info("")

            # Generate and display file tree
            tree_display = generate_file_tree(file_relative_paths, show_all=len(files_to_process) <= config.MAX_TREE_DISPLAY_MEDIUM)
            logging.info("Output file tree:")
            for line in tree_display.split('\n'):
                if line.strip():  # Skip empty lines
                    logging.info(f"  {line}")
            logging.info("")

        # Process documents with enhanced error handling
        results = []
        total_pages = 0
        for processed_count, file_path in enumerate(files_to_process, start=1):
            try:
                # Enhanced logging for preserve structure mode
                if args.preserve_structure:
                    relative_path = file_relative_paths.get(file_path, os.path.basename(file_path))
                    logging.info(f"Processing [{processed_count}/{len(files_to_process)}]: {file_path} -> {relative_path}")
                else:
                    logging.info(f"Processing [{processed_count}/{len(files_to_process)}]: {file_path}")

                # Use wrapper's backward-compatible interface
                result = processor.process_document(file_path, ocr_args)
                results.append(result)

                # Track page count for statistics
                pages = result.get('pages', 0)
                if pages == 0:
                    # Estimate pages if not available (assume at least 1 page per successful file)
                    pages = 1 if result['success'] else 0
                total_pages += pages

                # Get relative path for structure preservation
                relative_path = file_relative_paths.get(file_path, os.path.basename(file_path))

                # Save the result with error handling
                try:
                    output_file_path = get_output_file_path(
                        file_path,
                        args.output_dir,
                        preserve_structure=args.preserve_structure,
                        relative_path=relative_path,
                        base_dir=base_dir
                    )

                    # Use cached directory creation
                    dir_cache.ensure_directory(os.path.dirname(output_file_path))

                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(result['final_content'])

                    logging.debug(f"Saved output to: {output_file_path}")

                except OSError as e:
                    logging.error(f"Failed to save output file for {file_path}: {e}")
                    # Mark as failed if file saving failed
                    result['success'] = False
                    result['error'] = f"File save error: {e}"

                status = "SUCCESS" if result['success'] else "FAILED"
                method = result['chosen_method']
                processing_time = result.get('processing_time', 0)
                logging.info(f"  -> {status} (Method: {method}, Time: {processing_time:.2f}s, Pages: {pages})")

                if not result['success'] and 'error' in result:
                    logging.warning(f"  -> Error details: {result['error']}")

            except Exception as e:
                # Handle unexpected errors during processing
                logging.error(f"Unexpected error processing {file_path}: {e}")
                if args.verbose:
                    import traceback
                    logging.debug(traceback.format_exc())

                # Add failed result to maintain count accuracy
                error_result = {
                    'success': False,
                    'error': f"Unexpected error: {e}",
                    'chosen_method': 'none',
                    'processing_time': 0,
                    'final_content': '',
                    'file_name': os.path.basename(file_path)
                }
                results.append(error_result)

        # Display results summary
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)

        total_files = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total_files - successful
        success_rate = (successful / total_files * 100) if total_files > 0 else 0

        # Calculate detailed timing statistics
        total_processing_time = sum(r.get('processing_time', 0) for r in results)
        average_time_per_file = total_processing_time / total_files if total_files > 0 else 0
        average_time_per_page = total_processing_time / total_pages if total_pages > 0 else 0

        # Calculate overall conversion time
        conversion_end_time = time.time()
        total_conversion_time = conversion_end_time - conversion_start_time
        overhead_time = total_conversion_time - total_processing_time

        print(f"Total files processed: {total_files}")
        print(f"Total pages processed: {total_pages}")
        print(f"Successful conversions: {successful}")
        print(f"Failed conversions: {failed}")
        print(f"Success rate: {success_rate:.1f}%")
        print("")
        print("PERFORMANCE METRICS:")
        print(f"Total conversion time: {total_conversion_time:.2f}s")
        print(f"Pure processing time: {total_processing_time:.2f}s")
        print(f"Overhead time (I/O, setup): {overhead_time:.2f}s ({overhead_time/total_conversion_time*100:.1f}%)")
        print(f"Average time per file: {average_time_per_file:.2f}s")
        if total_pages > 0:
            print(f"Average time per page: {average_time_per_page:.2f}s")
            print(f"Processing throughput: {total_pages/total_processing_time:.1f} pages/sec")

        # Basic processing statistics (OCR-focused)
        stats = processor.get_detailed_statistics() if hasattr(processor, 'get_detailed_statistics') else processor.get_statistics()
        print("\nProcessing Stats:")
        if 'success_rate' in stats:
            print(f"  Success rate: {stats['success_rate']:.1f}%")

        # Determine output directory for display - must match get_output_file_path logic
        if args.preserve_structure:
            structure_note = " (preserving directory structure)"
            if args.output_dir:
                output_directory = args.output_dir
            else:
                # For preserve structure mode, use input base directory
                output_directory = os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        else:
            structure_note = " (flat structure)"
            output_directory = args.output_dir if args.output_dir else os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        print(f"Output directory: {output_directory}{structure_note}")

        # Display structure preservation summary for preserve structure mode
        if args.preserve_structure and successful > 0:
            print("\nDirectory Structure Summary:")
            print(f"  Input base: {base_dir}")
            print(f"  Output base: {output_directory}")
            print(f"  Structure preserved: {successful} files in their original hierarchy")
            if len(files_to_process) > 1:
                unique_dirs = set()
                for file_path in files_to_process:
                    relative_path = file_relative_paths.get(file_path, os.path.basename(file_path))
                    rel_dir = os.path.dirname(relative_path)
                    if rel_dir and rel_dir != '.':
                        unique_dirs.add(rel_dir)
                if unique_dirs:
                    print(f"  Directories created: {len(unique_dirs)} subdirectories")

        # List failed files if any
        if failed > 0:
            print("\nFailed files:")
            for file_result in results:
                if not file_result['success']:
                    error = file_result.get('error', 'Unknown error')
                    print(f"  - {file_result['file_name']}: {error}")

        print(f"\nConversion completed! Files saved to: {output_directory}{structure_note}")

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
