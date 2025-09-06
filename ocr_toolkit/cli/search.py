"""
CLI for creating searchable PDF documents.
"""

import os
import shutil
import argparse
import logging
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import ocrmypdf
from doctr.io import DocumentFile
from tqdm import tqdm

from .. import config
from ..utils import load_ocr_model, discover_pdf_files, add_common_ocr_args


def setup_logging():
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("ocrmypdf").setLevel(logging.ERROR)  # Suppress noisy ocrmypdf logs


def build_hocr(page_result, page_dims):
    """Builds an hOCR string from a single page result."""
    hocr_page = ET.Element("div", attrib={"class": "ocr_page"})
    hocr_page.set("title", f"image; bbox 0 0 {page_dims[0]} {page_dims[1]}")
    
    for block in page_result.blocks:
        for line in block.lines:
            line_bbox = f"bbox {int(line.geometry[0][0] * page_dims[0])} {int(line.geometry[0][1] * page_dims[1])} {int(line.geometry[1][0] * page_dims[0])} {int(line.geometry[1][1] * page_dims[1])}"
            hocr_line = ET.SubElement(
                hocr_page, "span", attrib={"class": "ocr_line", "title": line_bbox}
            )
            
            for word in line.words:
                word_bbox = f"bbox {int(word.geometry[0][0] * page_dims[0])} {int(word.geometry[0][1] * page_dims[1])} {int(word.geometry[1][0] * page_dims[0])} {int(word.geometry[1][1] * page_dims[1])}"
                hocr_word = ET.SubElement(
                    hocr_line, "span", attrib={"class": "ocrx_word", "title": word_bbox}
                )
                hocr_word.text = word.value
    
    return ET.tostring(hocr_page, encoding="unicode", method="xml")


def process_pdf(input_pdf, output_pdf, model, args):
    """Processes a single PDF file to make it searchable."""
    logging.info(f"Processing file: {input_pdf} -> {output_pdf}")
    
    # Create safe temp directory name by removing problematic characters
    safe_name = os.path.basename(input_pdf).replace(' ', '_').replace('.pdf', '')
    temp_dir = f"temp_hocr_{safe_name}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        doc = DocumentFile.from_pdf(input_pdf)
    except Exception as e:
        logging.error(f"Failed to load PDF {input_pdf}: {e}")
        return False
    
    hocr_files = []
    with tqdm(total=len(doc), desc="  - OCR Pages", unit="page") as pbar:
        for i in range(0, len(doc), args.batch_size):
            batch = doc[i : i + args.batch_size]
            result = model(batch)
            
            for page_idx, (page, page_result) in enumerate(zip(batch, result.pages)):
                page_dims = (page.shape[1], page.shape[0])
                hocr_content = build_hocr(page_result, page_dims)
                hocr_filename = os.path.join(temp_dir, f"page_{i+page_idx:04d}.hocr")
                with open(hocr_filename, "w", encoding="utf-8") as f:
                    f.write(hocr_content)
                hocr_files.append(hocr_filename)
                pbar.update(1)
    
    logging.info("Combining hOCR files into a single sidecar file...")
    sidecar_path = os.path.join(temp_dir, "sidecar.hocr")
    with open(sidecar_path, "w", encoding="utf-8") as outfile:
        outfile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        outfile.write(
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        )
        outfile.write(
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n<head>\n</head>\n<body>\n'
        )
        for fname in sorted(hocr_files):
            with open(fname, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
        outfile.write("</body>\n</html>\n")
    
    logging.info("Running ocrmypdf to create final searchable PDF...")
    try:
        # Configure ocrmypdf parameters to avoid common issues
        ocr_params = {
            'input_file': input_pdf,
            'output_file': output_pdf,
            'sidecar': sidecar_path,
            'optimize': args.optimize,
            'redo_ocr': True,
            'progress_bar': False,
        }
        
        # Add JBIG2 avoidance for compatibility
        if hasattr(args, 'no_jbig2') and args.no_jbig2:
            ocr_params['jbig2_lossy'] = False
            ocr_params['optimize'] = 0  # Disable optimization to avoid JBIG2
            logging.info("JBIG2 optimization disabled for compatibility")
        
        ocrmypdf.ocr(**ocr_params)
        logging.info(f"Successfully created searchable PDF: {output_pdf}")
        return True
    except subprocess.CalledProcessError as e:
        if 'jbig2' in str(e).lower():
            logging.error(f"JBIG2 compression failed. Try running with --no-jbig2 or --optimize 0")
            logging.error("This usually happens when JBIG2 tools are missing or incompatible")
            logging.error(f"Command that failed: {e.cmd}")
        else:
            logging.error(f"ocrmypdf subprocess failed for {input_pdf}: {e}")
        return False
    except FileNotFoundError as e:
        logging.error(f"Required tool not found: {e}")
        logging.error("Please ensure all ocrmypdf dependencies are properly installed")
        return False
    except Exception as e:
        logging.error(f"ocrmypdf failed for {input_pdf}: {e}")
        logging.error("You can try:")
        logging.error("  1. Use --optimize 0 to disable optimization")
        logging.error("  2. Use --no-jbig2 to avoid JBIG2 compression")
        logging.error("  3. Check if all required tools are installed")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_parser():
    """Create argument parser for search command."""
    parser = argparse.ArgumentParser(
        description="Create searchable PDFs from scanned PDF documents.",
        prog="ocr-search"
    )
    parser.add_argument(
        "input_path", 
        help="Path to PDF file or directory containing PDF files"
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        default=None,
        help="Output path for searchable PDF(s). Optional for directory input."
    )
    parser.add_argument(
        "-O", "--optimize",
        type=int,
        default=1,
        choices=[0, 1, 2, 3],
        help="Set ocrmypdf optimization level (0-3). Default is 1 (levels 2-3 require pngquant)."
    )
    parser.add_argument(
        "--no-jbig2",
        action="store_true",
        help="Disable JBIG2 compression to avoid compatibility issues with some systems."
    )
    
    # Add common OCR arguments
    add_common_ocr_args(parser)
    
    return parser


def main():
    """Main entry point for ocr-search command."""
    setup_logging()
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Load OCR model
        model = load_ocr_model(args.det_arch, args.reco_arch, args.cpu)
        
        # Discover PDF files
        pdf_files, base_dir = discover_pdf_files(args.input_path)
        if not pdf_files:
            logging.error("No PDF files found to process.")
            sys.exit(1)
        
        # Handle directory vs single file processing
        if os.path.isdir(args.input_path):
            # Directory processing
            output_dir = args.output_path or os.path.join(base_dir, config.DEFAULT_OCR_OUTPUT_DIR)
            logging.info(f"Output will be saved in: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            
            success_count = 0
            for i, pdf_file in enumerate(pdf_files):
                logging.info(f"--- Starting file {i+1}/{len(pdf_files)} ---")
                output_file = os.path.join(output_dir, os.path.basename(pdf_file))
                if process_pdf(pdf_file, output_file, model, args):
                    success_count += 1
            
            logging.info(f"Directory processing completed! {success_count}/{len(pdf_files)} files processed successfully.")
        else:
            # Single file processing
            if not args.output_path:
                logging.error("Output path must be specified for single file processing.")
                sys.exit(1)
            
            output_file = args.output_path
            if os.path.isdir(output_file):
                output_file = os.path.join(output_file, os.path.basename(args.input_path))
            
            if process_pdf(args.input_path, output_file, model, args):
                logging.info("Single file processing completed successfully!")
            else:
                logging.error("Failed to process the file.")
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