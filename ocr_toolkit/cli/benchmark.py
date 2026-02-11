"""
CLI for OCR performance benchmarking.
"""

import argparse
import logging
import os
import sys

from ..utils import (
    add_common_ocr_args,
    configure_logging_level,
    configure_paddle_environment,
    configure_paddle_warnings,
    discover_pdf_files,
)


def setup_logging():
    """Configure logging for CLI usage."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def create_parser():
    """Create argument parser for benchmark command."""
    parser = argparse.ArgumentParser(
        description="Run OCR performance benchmarks on PDF files.", prog="ocr-bench"
    )
    parser.add_argument(
        "input_path", help="Path to directory containing PDF files for benchmarking"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes for multiprocessing (default: 1)",
    )
    parser.add_argument(
        "--file-limit",
        type=int,
        default=None,
        help="Limit the number of files to process (default: no limit)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout per file in seconds (default: 300)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Add common OCR arguments
    add_common_ocr_args(parser)

    return parser


import warnings

# Suppress noisy NumPy warnings on Windows (especially with version 1.26.x)
warnings.filterwarnings(
    "ignore", message="Numpy built with MINGW-W64 on Windows 64 bits is experimental"
)
warnings.filterwarnings("ignore", message="invalid value encountered in exp2")
warnings.filterwarnings("ignore", message="invalid value encountered in log10")
warnings.filterwarnings("ignore", message="invalid value encountered in nextafter")


def main():
    """Main entry point for ocr-bench command."""
    configure_paddle_environment()
    configure_paddle_warnings()
    setup_logging()
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging_level(args)

    try:
        if getattr(args, "threads", None):
            os.environ["OMP_NUM_THREADS"] = str(args.threads)
            os.environ["MKL_NUM_THREADS"] = str(args.threads)

        # Import benchmark module
        from .. import benchmark

        # Discover PDF files
        pdf_files, base_dir = discover_pdf_files(args.input_path)
        if not pdf_files:
            logging.error("No PDF files found for benchmarking.")
            sys.exit(1)

        # Apply file limit if specified
        if args.file_limit:
            pdf_files = pdf_files[: args.file_limit]
            logging.info(f"Limited to first {len(pdf_files)} files")

        logging.info("Starting OCR benchmark...")
        logging.info(f"Batch size: {args.batch_size}")
        logging.info(f"Workers: {args.workers}")
        logging.info(f"Using {'GPU' if not args.cpu else 'CPU'}")
        logging.info(f"Found {len(pdf_files)} PDF files to process")

        # Run benchmark
        results = benchmark.run_benchmark(
            pdf_files=pdf_files,
            batch_size=args.batch_size,
            workers=args.workers,
            use_cpu=args.cpu,
            timeout=args.timeout,
            fast=getattr(args, "fast", False),
            pages=getattr(args, "pages", None),
            profile=getattr(args, "profile", False),
            threads=getattr(args, "threads", None),
        )

        # Print results summary
        print("\n" + "=" * 60)
        print("BENCHMARK REPORT")
        print("=" * 60)
        print(f"Files processed: {results['files_processed']}")
        print(f"Successful: {results['successful_files']}")
        print(f"Failed: {results['failed_files']}")
        print(f"Total benchmark time: {results['total_time']:.2f}s")
        print(f"Average time per file: {results['avg_time_per_file']:.2f}s")
        print(f"Processing rate: {results['files_per_second']:.2f} files/second")
        if results["processing_times"]:
            print(f"Fastest file: {min(results['processing_times']):.2f}s")
            print(f"Slowest file: {max(results['processing_times']):.2f}s")
        print("=" * 60)

        logging.info("Benchmark completed successfully")

    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Benchmark cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during benchmark: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
