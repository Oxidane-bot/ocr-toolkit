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

# Suppress noisy NumPy warnings on Windows (especially with version 1.26.x)
# Must be done before importing numpy or other libraries that use it
warnings.filterwarnings("ignore", message="Numpy built with MINGW-W64 on Windows 64 bits is experimental")
warnings.filterwarnings("ignore", message="invalid value encountered in exp2")
warnings.filterwarnings("ignore", message="invalid value encountered in log10")
warnings.filterwarnings("ignore", message="invalid value encountered in nextafter")

# Suppress PaddlePaddle/PaddleOCR API warnings
warnings.filterwarnings("ignore", message="Non compatible API")
warnings.filterwarnings("ignore", message="To copy construct from a tensor")

from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .. import config
from ..processors.excel_processor import ExcelDataProcessor
from ..processors.text_file_processor import TextFileProcessor
from ..utils import (
    BaseArgumentParser,
    add_common_ocr_args,
    add_output_args,
    check_input_path_exists,
    configure_logging_level,
    configure_paddle_environment,
    discover_files,
    generate_file_tree,
    get_directory_cache,
    get_output_file_path,
    load_ocr_model,
    setup_logging,
    validate_common_arguments,
)


def _apply_threads_env(threads: int | None) -> None:
    if threads and threads > 0:
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)


def _determine_output_directory(args, base_dir: str) -> str:
    """
    Determine the output directory based on arguments.

    Args:
        args: Command line arguments
        base_dir: Base input directory

    Returns:
        Output directory path
    """
    if args.preserve_structure:
        if args.output_dir:
            return args.output_dir
        return os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
    else:
        return args.output_dir or os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)


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
    # Configure PaddlePaddle environment before any imports
    configure_paddle_environment()

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
        _apply_threads_env(getattr(args, "threads", None))

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
            batch_size=1,  # Default batch size for compatibility
            cpu=args.cpu,
            engine=getattr(args, 'engine', 'paddleocr')
        )

        # Lazily load OCR model only if any file requires it.
        model_required_exts = {
            '.pdf',
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif',
            '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'
        }
        needs_ocr_model = any(Path(p).suffix.lower() in model_required_exts for p in files_to_process)

        processor = None
        if needs_ocr_model:
            # Verify PaddlePaddle installation
            logging.info("Verifying PaddlePaddle installation...")
            load_ocr_model(use_cpu=ocr_args.cpu)

            # Import lazily to avoid pulling in heavy OCR deps on non-OCR workloads.
            from .. import ocr_processor_wrapper
            processor = ocr_processor_wrapper.create_ocr_processor_wrapper(
                use_gpu=not ocr_args.cpu,
                with_images=getattr(args, 'with_images', False)
            )
        else:
            logging.info("No OCR-required formats detected; skipping OCR model load.")

        # Get directory cache for optimized directory creation
        dir_cache = get_directory_cache()
        dir_cache.reset()  # Reset cache for this conversion session

        # Display output directory structure preview for preserve structure mode
        if args.preserve_structure and len(files_to_process) > 1:
            # Determine output directory for preview - must match get_output_file_path logic
            output_directory = _determine_output_directory(args, base_dir)

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
        file_index = {file_path: idx for idx, file_path in enumerate(files_to_process, start=1)}

        # Only parallelize formats that never touch GPU/COM conversion in our pipeline.
        parallel_safe_exts = {'.txt', '.md', '.rtf', '.xlsx'}
        parallel_file_set = {p for p in files_to_process if Path(p).suffix.lower() in parallel_safe_exts}
        parallel_files = [p for p in files_to_process if p in parallel_file_set]
        serial_files = [p for p in files_to_process if p not in parallel_file_set]

        if args.workers > 1 and parallel_files:
            logging.info(
                f"Using {args.workers} workers for text/Excel files; other formats processed serially for GPU/Office safety."
            )

        def process_and_save(file_path: str) -> tuple[dict, int]:
            processed_count = file_index.get(file_path, 0)
            relative_path = file_relative_paths.get(file_path, os.path.basename(file_path))

            try:
                # Enhanced logging for preserve structure mode - use print to avoid being drowned by PaddlePaddle stderr
                if args.preserve_structure:
                    print(f"Processing [{processed_count}/{len(files_to_process)}]: {file_path} -> {relative_path}")
                else:
                    print(f"Processing [{processed_count}/{len(files_to_process)}]: {file_path}")

                ext = Path(file_path).suffix.lower()

                if processor is not None:
                    # Calculate output directory for this file (needed for image extraction)
                    output_file_path = get_output_file_path(
                        file_path,
                        args.output_dir,
                        preserve_structure=args.preserve_structure,
                        relative_path=relative_path,
                        base_dir=base_dir
                    )
                    output_dir = os.path.dirname(output_file_path)

                    # Add output directory to args for image extraction
                    args._output_dir = output_dir

                    # Use wrapper's backward-compatible interface
                    result = processor.process_document(file_path, args)
                else:
                    # Light path: handle text / xlsx without loading OCR model.
                    start_time = time.time()
                    text_processor = TextFileProcessor()
                    excel_processor = ExcelDataProcessor()

                    if ext in {'.txt', '.md', '.rtf'}:
                        content = text_processor.process_file(file_path)
                        result = {
                            'file_path': file_path,
                            'file_name': os.path.basename(file_path),
                            'success': True,
                            'chosen_method': 'ocr',
                            'final_content': content,
                            'processing_time': time.time() - start_time,
                            'pages': 1,
                            'comparison': {},
                            'ocr_result': {'success': True, 'content': content, 'error': ''},
                            'temp_files': [],
                            'error': ''
                        }
                    elif ext == '.xlsx':
                        excel_result = excel_processor.process(file_path)
                        result = {
                            'file_path': file_path,
                            'file_name': os.path.basename(file_path),
                            'success': excel_result.success,
                            'chosen_method': 'ocr',
                            'final_content': excel_result.content if excel_result.success else '',
                            'processing_time': excel_result.processing_time,
                            'pages': excel_result.pages,
                            'comparison': {},
                            'ocr_result': {'success': excel_result.success, 'content': excel_result.content, 'error': excel_result.error},
                            'temp_files': [],
                            'error': excel_result.error if not excel_result.success else ''
                        }
                    else:
                        result = {
                            'file_path': file_path,
                            'file_name': os.path.basename(file_path),
                            'success': False,
                            'chosen_method': 'none',
                            'final_content': '',
                            'processing_time': time.time() - start_time,
                            'pages': 0,
                            'comparison': {},
                            'ocr_result': {'success': False, 'content': '', 'error': f'Unsupported file format: {ext}'},
                            'temp_files': [],
                            'error': f'Unsupported file format: {ext}'
                        }

                # Track page count for statistics
                pages = result.get('pages', 0)
                if pages == 0:
                    pages = 1 if result.get('success') else 0

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
                        f.write(result.get('final_content', ''))

                    logging.debug(f"Saved output to: {output_file_path}")

                except OSError as e:
                    logging.error(f"Failed to save output file for {file_path}: {e}")
                    result['success'] = False
                    result['error'] = f"File save error: {e}"

                status = "SUCCESS" if result.get('success') else "FAILED"
                method = result.get('chosen_method', 'none')
                processing_time = result.get('processing_time', 0)
                logging.info(f"  -> {status} (Method: {method}, Time: {processing_time:.2f}s, Pages: {pages})")

                if not result.get('success') and result.get('error'):
                    logging.warning(f"  -> Error details: {result['error']}")

                if getattr(args, "profile", False):
                    profile = result.get("ocr_result", {}).get("metadata", {}).get("profile")
                    if isinstance(profile, dict) and profile:
                        logging.info("  -> Profile breakdown:")
                        for name, data in sorted(
                            profile.items(),
                            key=lambda kv: float(kv[1].get("total_s", 0.0)),
                            reverse=True,
                        ):
                            total_s = float(data.get("total_s", 0.0))
                            count = int(data.get("count", 0))
                            logging.info(f"     - {name}: {total_s:.3f}s (n={count})")

                return result, pages

            except Exception as e:
                # Handle unexpected errors during processing
                logging.error(f"Unexpected error processing {file_path}: {e}")
                if args.verbose:
                    import traceback
                    logging.debug(traceback.format_exc())

                error_result = {
                    'success': False,
                    'error': f"Unexpected error: {e}",
                    'chosen_method': 'none',
                    'processing_time': 0,
                    'final_content': '',
                    'file_name': os.path.basename(file_path)
                }
                return error_result, 0

        futures = []
        if args.workers > 1 and parallel_files:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = [executor.submit(process_and_save, file_path) for file_path in parallel_files]

                # Process OCR/Office-heavy formats serially in main thread while workers handle safe formats.
                for file_path in serial_files:
                    result, pages = process_and_save(file_path)
                    results.append(result)
                    total_pages += pages

                for future in as_completed(futures):
                    result, pages = future.result()
                    results.append(result)
                    total_pages += pages
        else:
            for file_path in files_to_process:
                result, pages = process_and_save(file_path)
                results.append(result)
                total_pages += pages

        # Display results summary
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)

        total_files = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total_files - successful
        success_rate = (successful / total_files * 100) if total_files > 0 else 0

        # Calculate detailed timing statistics
        sum_processing_time = sum(r.get('processing_time', 0) for r in results)
        average_time_per_file = sum_processing_time / total_files if total_files > 0 else 0
        average_time_per_page = sum_processing_time / total_pages if total_pages > 0 else 0

        # Calculate overall conversion time
        conversion_end_time = time.time()
        total_conversion_time = conversion_end_time - conversion_start_time

        # In parallel mode, per-file processing times overlap; use a critical-path estimate.
        used_parallel = args.workers > 1 and bool(parallel_files)
        if used_parallel:
            serial_processing_time = sum(
                r.get('processing_time', 0)
                for r in results
                if Path(r.get('file_path', '')).suffix.lower() not in parallel_safe_exts
            )
            parallel_processing_times = [
                r.get('processing_time', 0)
                for r in results
                if Path(r.get('file_path', '')).suffix.lower() in parallel_safe_exts
            ]
            parallel_max_processing_time = max(parallel_processing_times, default=0)
            effective_processing_time = max(serial_processing_time, parallel_max_processing_time)
        else:
            effective_processing_time = sum_processing_time

        overhead_time = max(0.0, total_conversion_time - effective_processing_time)

        print(f"Total files processed: {total_files}")
        print(f"Total pages processed: {total_pages}")
        print(f"Successful conversions: {successful}")
        print(f"Failed conversions: {failed}")
        print(f"Success rate: {success_rate:.1f}%")
        print("")
        print("PERFORMANCE METRICS:")
        print(f"Total conversion time: {total_conversion_time:.2f}s")
        if used_parallel:
            print(f"Critical path processing time: {effective_processing_time:.2f}s")
            print(f"Sum of per-file processing time: {sum_processing_time:.2f}s")
        else:
            print(f"Pure processing time: {sum_processing_time:.2f}s")
        print(f"Overhead time (I/O, setup): {overhead_time:.2f}s ({overhead_time/total_conversion_time*100:.1f}%)")
        print(f"Average time per file: {average_time_per_file:.2f}s")
        if total_pages > 0:
            print(f"Average time per page: {average_time_per_page:.2f}s")
            print(f"Processing throughput (wall): {total_pages/total_conversion_time:.1f} pages/sec")

        # Basic processing statistics (OCR-focused)
        if processor is not None:
            stats = processor.get_detailed_statistics() if hasattr(processor, 'get_detailed_statistics') else processor.get_statistics()
        else:
            stats = {'success_rate': success_rate}
        print("\nProcessing Stats:")
        if 'success_rate' in stats:
            print(f"  Success rate: {stats['success_rate']:.1f}%")

        # Determine output directory for display - must match get_output_file_path logic
        if args.preserve_structure:
            structure_note = " (preserving directory structure)"
        else:
            structure_note = " (flat structure)"
        output_directory = _determine_output_directory(args, base_dir)
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
