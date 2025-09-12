"""
Universal Office document to PDF converter using Microsoft Office COM automation.

This script converts various Office document formats to PDF using the installed
Microsoft Office applications via COM automation.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil

# Add project root to path for importing utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from ocr_toolkit.utils import setup_logging as setup_logging_shared


def setup_logging():
    """Configure logging for the converter."""
    setup_logging_shared()


def convert_docx_to_pdf_simple(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert DOCX to PDF using docx2pdf library (fastest for .docx files).
    
    Args:
        input_path: Path to input DOCX file
        output_path: Path to output PDF file
        
    Returns:
        Dictionary with conversion results
    """
    result = {
        'method': 'docx2pdf',
        'success': False,
        'processing_time': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        from docx2pdf import convert
        convert(input_path, output_path)
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using docx2pdf")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"docx2pdf conversion failed for {input_path}: {e}")
    
    result['processing_time'] = time.time() - start_time
    return result


def convert_with_word_com(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert Word document to PDF using Word COM automation.
    
    Args:
        input_path: Path to input Word file (.doc, .docx)
        output_path: Path to output PDF file
        
    Returns:
        Dictionary with conversion results
    """
    result = {
        'method': 'word_com',
        'success': False,
        'processing_time': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        import win32com.client
        
        # Create Word application
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        # Open document
        doc = word.Documents.Open(os.path.abspath(input_path))
        
        # Export as PDF (format 17 = PDF)
        doc.ExportAsFixedFormat(
            OutputFileName=os.path.abspath(output_path),
            ExportFormat=17,  # PDF format
            OpenAfterExport=False,
            OptimizeFor=0,  # Print optimization
            BitmapMissingFonts=True,
            DocStructureTags=True,
            CreateBookmarks=0,
            IncludeMarkup=False
        )
        
        # Close document and quit Word
        doc.Close()
        word.Quit()
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using Word COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Word COM conversion failed for {input_path}: {e}")
        try:
            if 'doc' in locals():
                doc.Close()
            if 'word' in locals():
                word.Quit()
        except:
            pass
    
    result['processing_time'] = time.time() - start_time
    return result


def convert_with_powerpoint_com(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert PowerPoint presentation to PDF using PowerPoint COM automation.
    
    Args:
        input_path: Path to input PowerPoint file (.ppt, .pptx)
        output_path: Path to output PDF file
        
    Returns:
        Dictionary with conversion results
    """
    result = {
        'method': 'powerpoint_com',
        'success': False,
        'processing_time': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        import win32com.client
        
        # Create PowerPoint application
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = 1  # PowerPoint needs to be visible for some operations
        
        # Open presentation
        presentation = powerpoint.Presentations.Open(
            os.path.abspath(input_path), 
            ReadOnly=True, 
            Untitled=True, 
            WithWindow=False
        )
        
        # Export as PDF (format 32 = PDF)
        presentation.SaveAs(
            os.path.abspath(output_path), 
            32  # PDF format
        )
        
        # Close presentation and quit PowerPoint
        presentation.Close()
        powerpoint.Quit()
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using PowerPoint COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"PowerPoint COM conversion failed for {input_path}: {e}")
        try:
            if 'presentation' in locals():
                presentation.Close()
            if 'powerpoint' in locals():
                powerpoint.Quit()
        except:
            pass
    
    result['processing_time'] = time.time() - start_time
    return result


def convert_with_excel_com(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert Excel workbook to PDF using Excel COM automation.
    
    Args:
        input_path: Path to input Excel file (.xls, .xlsx)
        output_path: Path to output PDF file
        
    Returns:
        Dictionary with conversion results
    """
    result = {
        'method': 'excel_com',
        'success': False,
        'processing_time': 0,
        'error': ''
    }
    
    start_time = time.time()
    
    try:
        import win32com.client
        
        # Create Excel application
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        # Open workbook
        workbook = excel.Workbooks.Open(os.path.abspath(input_path))
        
        # Export as PDF (xlTypePDF = 0)
        workbook.ExportAsFixedFormat(
            Type=0,  # PDF format
            Filename=os.path.abspath(output_path),
            Quality=0,  # Standard quality
            IncludeDocProps=True,
            IgnorePrintAreas=False,
            OpenAfterPublish=False
        )
        
        # Close workbook and quit Excel
        workbook.Close()
        excel.Quit()
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using Excel COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Excel COM conversion failed for {input_path}: {e}")
        try:
            if 'workbook' in locals():
                workbook.Close()
            if 'excel' in locals():
                excel.Quit()
        except:
            pass
    
    result['processing_time'] = time.time() - start_time
    return result


def convert_office_to_pdf(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convert any supported Office document to PDF using the appropriate method.
    
    Args:
        input_path: Path to input Office file
        output_path: Path to output PDF file
        
    Returns:
        Dictionary with conversion results
    """
    if not os.path.exists(input_path):
        return {
            'method': 'none',
            'success': False,
            'processing_time': 0,
            'error': f'Input file does not exist: {input_path}'
        }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Get file extension
    ext = Path(input_path).suffix.lower()
    
    # Handle PDF files (just copy)
    if ext == '.pdf':
        try:
            shutil.copy2(input_path, output_path)
            return {
                'method': 'copy',
                'success': True,
                'processing_time': 0.001,  # Minimal time for copy
                'error': ''
            }
        except Exception as e:
            return {
                'method': 'copy',
                'success': False,
                'processing_time': 0,
                'error': str(e)
            }
    
    # Choose conversion method based on file type
    if ext == '.docx':
        # Try docx2pdf first (faster), fall back to COM if it fails
        result = convert_docx_to_pdf_simple(input_path, output_path)
        if not result['success']:
            logging.warning("docx2pdf failed, trying Word COM automation")
            result = convert_with_word_com(input_path, output_path)
        return result
    
    elif ext in ['.doc']:
        return convert_with_word_com(input_path, output_path)
    
    elif ext in ['.ppt', '.pptx']:
        return convert_with_powerpoint_com(input_path, output_path)
    
    elif ext in ['.xls', '.xlsx']:
        return convert_with_excel_com(input_path, output_path)
    
    else:
        return {
            'method': 'none',
            'success': False,
            'processing_time': 0,
            'error': f'Unsupported file format: {ext}'
        }


def batch_convert_to_pdf(input_dir: str, output_dir: str) -> Dict[str, Any]:
    """
    Convert all supported Office documents in a directory to PDF.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory for output PDF files
        
    Returns:
        Dictionary with batch conversion results
    """
    setup_logging()
    
    supported_extensions = {'.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}
    
    # Find all supported files
    input_files = []
    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)
        if os.path.isfile(filepath) and Path(filepath).suffix.lower() in supported_extensions:
            input_files.append(filepath)
    
    logging.info(f"Found {len(input_files)} files to convert")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert each file
    results = []
    total_start_time = time.time()
    
    for i, input_file in enumerate(input_files, 1):
        filename = os.path.basename(input_file)
        name_without_ext = os.path.splitext(filename)[0]
        output_file = os.path.join(output_dir, f"{name_without_ext}.pdf")
        
        logging.info(f"Converting {i}/{len(input_files)}: {filename}")
        
        result = convert_office_to_pdf(input_file, output_file)
        result['input_file'] = input_file
        result['output_file'] = output_file
        result['filename'] = filename
        
        results.append(result)
        
        status = "✓" if result['success'] else "✗"
        logging.info(f"  {status} {result['method']} ({result['processing_time']:.2f}s)")
        
        if not result['success']:
            logging.error(f"  Error: {result['error']}")
    
    total_time = time.time() - total_start_time
    successful = sum(1 for r in results if r['success'])
    
    logging.info(f"\nBatch conversion completed:")
    logging.info(f"  Total files: {len(input_files)}")
    logging.info(f"  Successful: {successful}")
    logging.info(f"  Failed: {len(input_files) - successful}")
    logging.info(f"  Total time: {total_time:.2f}s")
    
    return {
        'total_files': len(input_files),
        'successful': successful,
        'failed': len(input_files) - successful,
        'total_time': total_time,
        'results': results
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert Office documents to PDF")
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('output', help='Output file or directory')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if os.path.isfile(args.input):
        # Single file conversion
        result = convert_office_to_pdf(args.input, args.output)
        if result['success']:
            logging.info(f"Successfully converted {args.input} to {args.output}")
        else:
            logging.error(f"Conversion failed: {result['error']}")
            sys.exit(1)
    
    elif os.path.isdir(args.input):
        # Batch conversion
        batch_convert_to_pdf(args.input, args.output)
    
    else:
        logging.error(f"Input path does not exist: {args.input}")
        sys.exit(1)