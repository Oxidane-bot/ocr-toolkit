"""
CLI for text extraction from documents using OCR.
"""

import os
import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..utils import discover_files, load_ocr_model, add_common_ocr_args, add_output_args, get_directory_cache, get_output_file_path, setup_logging, BaseArgumentParser, configure_logging_level, check_input_path_exists
from ..processors import OCRProcessor
from .. import config, ocr_processor_wrapper


def create_parser():
    """Create argument parser for extract command."""
    parser = BaseArgumentParser.create_base_parser(
        prog="ocr-extract",
        description="Extract text from documents (PDF, images, Office docs) using intelligent dual-path processing."
    )
    
    BaseArgumentParser.add_input_path_argument(
        parser, 
        help="Path to document file or directory containing supported documents"
    )
    
    # Processing method options
    parser.add_argument(
        "--ocr-only",
        action="store_true",
        help="Use only OCR processing (disable MarkItDown)"
    )
    parser.add_argument(
        "--markitdown-only",
        action="store_true",
        help="Use only MarkItDown processing (disable OCR)"
    )
    parser.add_argument(
        "--show-selection",
        action="store_true",
        help="Show detailed selection reasoning and quality scores"
    )
    
    # Add common arguments
    add_common_ocr_args(parser)
    add_output_args(parser)
    
    return parser


def _apply_threads_env(threads: Optional[int]) -> None:
    if threads and threads > 0:
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)


def main():
    """Main entry point for ocr-extract command."""
    setup_logging()
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate arguments
    if args.ocr_only and args.markitdown_only:
        logging.error("Cannot use both --ocr-only and --markitdown-only options")
        sys.exit(1)
    
    # Configure logging
    configure_logging_level(args)

    # Auto defaults for Chinese (CnOCR) mode: threads=8, batch_size=32 unless explicitly overridden
    if getattr(args, 'zh', False):
        # If user didn't pass threads, default to 8
        if args.threads is None:
            args.threads = 8
            logging.debug("Defaulting threads to 8 for --zh mode")
        # If batch_size is still the global default, bump to 32
        try:
            if args.batch_size == config.DEFAULT_BATCH_SIZE:
                args.batch_size = 32
                logging.debug("Defaulting batch_size to 32 for --zh mode")
        except Exception:
            pass
    
    # Apply thread env overrides early
    _apply_threads_env(args.threads)
    
    try:
        # Load OCR model (always needed for dual processing or OCR-only)
        # Load doctr model only if not in markitdown-only mode AND not in Chinese mode
        model = None
        if not args.markitdown_only and not getattr(args, 'zh', False):
            model = load_ocr_model(args.det_arch, args.reco_arch, args.cpu)
        
        # Discover supported files
        recursive = not getattr(args, 'no_recursive', False)
        files, base_dir, file_relative_paths = discover_files(args.input_path, recursive=recursive)
        if not files:
            logging.error("No supported files found to process.")
            sys.exit(1)
        
        # Display file discovery info
        search_type = "recursively" if recursive else "non-recursively"
        logging.info(f"Searching {search_type} - found {len(files)} files from: {args.input_path}")
        if getattr(args, 'preserve_structure', False):
            logging.info("Directory structure will be preserved in output")
        
        # Set up output directory
        output_dir = args.output_dir or os.path.join(base_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        logging.info(f"Output will be saved to: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize processor based on mode
        if args.markitdown_only:
            processor = OCRProcessor(model, args.batch_size, use_cnocr=args.zh)
            processing_mode = "OCR only" + (" with CnOCR" if args.zh else "")
        elif args.ocr_only:
            processor = OCRProcessor(model, args.batch_size, use_cnocr=args.zh)
            processing_mode = "OCR only" + (" with CnOCR" if args.zh else "")
        else:
            processor = ocr_processor_wrapper.create_ocr_processor_wrapper(model, args.batch_size, use_zh=args.zh)
            processing_mode = "Intelligent OCR processing" + (" with CnOCR" if args.zh else "")
        if args.fast:
            processing_mode += " (fast)"
        if args.profile:
            processing_mode += " [profile]"
        
        # Get directory cache for optimized directory creation
        dir_cache = get_directory_cache()
        dir_cache.reset()  # Reset cache for this extraction session
        
        # Process files
        total_files = len(files)
        successful_files = 0
        total_processing_time = 0
        total_pages = 0  # Track page count
        method_stats = {'markitdown': 0, 'ocr': 0, 'failed': 0}
        
        logging.info(f"Processing {total_files} files using {processing_mode}...")
        print(f"\n🔄 Processing Mode: {processing_mode}")
        
        for i, file_path in enumerate(files, 1):
            try:
                logging.info(f"[{i}/{total_files}] Processing: {os.path.basename(file_path)}")
                
                # Process based on selected mode
                if args.markitdown_only or args.ocr_only:
                    result = processor.process(file_path, fast=args.fast, pages=args.pages, profile=args.profile)
                    # Convert ProcessingResult to dict for compatibility
                    result_dict = {
                        'success': result.success,
                        'content': result.content,
                        'final_content': result.content,  # For compatibility
                        'chosen_method': result.method,
                        'processing_time': result.processing_time,
                        'error': result.error
                    }
                else:
                    # Dual processing - use legacy interface
                    result_dict = processor.process_document(file_path, args)
                
                total_processing_time += result_dict.get('processing_time', 0)
                
                # Track page count for statistics  
                pages = result_dict.get('pages', 0)
                if pages == 0:
                    # Estimate pages if not available (assume at least 1 page per successful file)
                    pages = 1 if result_dict.get('success', False) else 0
                total_pages += pages
                
                if result_dict.get('success', False):
                    # Get relative path for structure preservation
                    relative_path = file_relative_paths.get(file_path, os.path.basename(file_path))
                    
                    # Save markdown output with optional structure preservation
                    output_file_path = get_output_file_path(
                        file_path,
                        output_dir,
                        preserve_structure=getattr(args, 'preserve_structure', False),
                        relative_path=relative_path,
                        base_dir=base_dir
                    )
                    # Use cached directory creation
                    dir_cache.ensure_directory(os.path.dirname(output_file_path))
                    
                    content = result_dict.get('final_content') or result_dict.get('content', '')
                    
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    successful_files += 1
                    
                    # Track method statistics
                    chosen_method = result_dict.get('chosen_method', 'unknown')
                    if chosen_method in method_stats:
                        method_stats[chosen_method] += 1
                    
                    # Show selection details if requested
                    if args.show_selection and 'comparison' in result_dict:
                        comparison = result_dict['comparison']
                        print(f"   📊 {comparison['selection_reason']}")
                        if 'quality_details' in comparison:
                            md_score = comparison.get('markitdown_score', 0)
                            ocr_score = comparison.get('ocr_score', 0)
                            print(f"   📈 Quality scores: MarkItDown={md_score:.1f}, OCR={ocr_score:.1f}")
                    
                    logging.info(f"✅ Successfully processed {os.path.basename(file_path)} → {chosen_method.upper()}")
                else:
                    method_stats['failed'] += 1
                    error = result_dict.get('error', 'Unknown error')
                    logging.error(f"❌ Failed to process {os.path.basename(file_path)}: {error}")
                    
            except Exception as e:
                method_stats['failed'] += 1
                logging.error(f"❌ Failed to process {file_path}: {e}")
                continue
        
        # Print comprehensive summary
        print("\n" + "="*80)
        print("📊 INTELLIGENT EXTRACTION SUMMARY")
        print("="*80)
        print(f"📁 Total files processed: {total_files}")
        print(f"📄 Total pages processed: {total_pages}")
        print(f"✅ Successful extractions: {successful_files}")
        print(f"❌ Failed extractions: {method_stats['failed']}")
        print(f"🎯 Success rate: {(successful_files/total_files*100):.1f}%")
        print(f"")
        print(f"⏱️  Total processing time: {total_processing_time:.2f}s")
        print(f"📊 Average time per file: {total_processing_time/total_files:.2f}s")
        if total_pages > 0:
            print(f"📊 Average time per page: {total_processing_time/total_pages:.2f}s")
        
        if not args.markitdown_only and not args.ocr_only:
            # Show method distribution for dual processing
            print(f"\n🧠 Method Selection Distribution:")
            if method_stats['markitdown'] > 0:
                print(f"   📝 MarkItDown chosen: {method_stats['markitdown']} files ({method_stats['markitdown']/successful_files*100:.1f}%)")
            if method_stats['ocr'] > 0:
                print(f"   🔍 OCR chosen: {method_stats['ocr']} files ({method_stats['ocr']/successful_files*100:.1f}%)")
            
            # Show dual processor statistics
            if hasattr(processor, 'get_statistics'):
                dual_stats = processor.get_statistics()
                print(f"\n📈 Processing Statistics:")
                print(f"   🎯 Overall success rate: {dual_stats.get('success_rate', 0):.1f}%")
                if dual_stats.get('markitdown_only', 0) > 0:
                    print(f"   📝 MarkItDown-only successes: {dual_stats['markitdown_only']}")
                if dual_stats.get('ocr_only', 0) > 0:
                    print(f"   🔍 OCR-only successes: {dual_stats['ocr_only']}")
        
        structure_note = " (preserving directory structure)" if getattr(args, 'preserve_structure', False) else " (flat structure)"
        print(f"\n📂 Output directory: {output_dir}{structure_note}")
        
        if successful_files == total_files:
            print("\n🎉 All files processed successfully!")
            logging.info("All files processed successfully!")
        else:
            print(f"\n⚠️  {total_files - successful_files} files failed to process.")
            logging.warning(f"{total_files - successful_files} files failed to process.")
            sys.exit(1)
                
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()