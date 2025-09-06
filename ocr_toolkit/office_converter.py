"""
Office document converter module for OCR toolkit.

This module provides functionality to convert Office documents to PDF
for subsequent OCR processing.
"""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional


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
    word = None
    doc = None
    
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
            CreateBookmarks=0
        )
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using Word COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Word COM conversion failed for {input_path}: {e}")
    
    finally:
        # Clean up COM objects
        try:
            if doc:
                doc.Close()
            if word:
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
    powerpoint = None
    presentation = None
    
    try:
        import win32com.client
        
        # Create PowerPoint application
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = False
        
        # Open presentation
        presentation = powerpoint.Presentations.Open(
            os.path.abspath(input_path), 
            ReadOnly=True, 
            Untitled=True, 
            WithWindow=False
        )
        
        # Export as PDF (format 32 = PDF)
        presentation.ExportAsFixedFormat(
            Path=os.path.abspath(output_path),
            FixedFormatType=2,  # PDF format
            Intent=1,  # Print intent
            FrameSlides=0,  # Don't frame slides
            HandoutOrder=1,
            OutputType=0  # All slides
        )
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using PowerPoint COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"PowerPoint COM conversion failed for {input_path}: {e}")
    
    finally:
        # Clean up COM objects
        try:
            if presentation:
                presentation.Close()
            if powerpoint:
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
    excel = None
    workbook = None
    
    try:
        import win32com.client
        
        # Create Excel application
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        # Open workbook
        workbook = excel.Workbooks.Open(os.path.abspath(input_path))
        
        # Export as PDF (format 0 = PDF)
        workbook.ExportAsFixedFormat(
            Type=0,  # PDF format
            Filename=os.path.abspath(output_path),
            Quality=0,  # Standard quality
            IncludeDocProps=True,
            IgnorePrintAreas=False,
            OpenAfterPublish=False
        )
        
        result['success'] = True
        logging.info(f"Successfully converted {input_path} to PDF using Excel COM")
        
    except Exception as e:
        result['error'] = str(e)
        logging.error(f"Excel COM conversion failed for {input_path}: {e}")
    
    finally:
        # Clean up COM objects
        try:
            if workbook:
                workbook.Close()
            if excel:
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
    ext = Path(input_path).suffix.lower()
    
    if ext == '.docx':
        # Try docx2pdf first (faster), fall back to COM if it fails
        result = convert_docx_to_pdf_simple(input_path, output_path)
        if not result['success']:
            logging.warning("docx2pdf failed, trying Word COM automation")
            result = convert_with_word_com(input_path, output_path)
        return result
    
    elif ext == '.doc':
        return convert_with_word_com(input_path, output_path)
    
    elif ext in ['.ppt', '.pptx']:
        return convert_with_powerpoint_com(input_path, output_path)
    
    elif ext in ['.xls', '.xlsx']:
        return convert_with_excel_com(input_path, output_path)
    
    else:
        return {
            'method': 'unsupported',
            'success': False,
            'processing_time': 0,
            'error': f'Unsupported file format: {ext}'
        }


def create_temp_pdf(input_path: str) -> Optional[str]:
    """
    Convert Office document to temporary PDF file for OCR processing.
    
    Args:
        input_path: Path to input Office file
        
    Returns:
        Path to temporary PDF file, or None if conversion failed
    """
    try:
        # Create temporary PDF file
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        # Convert to PDF
        result = convert_office_to_pdf(input_path, temp_pdf_path)
        
        if result['success']:
            logging.info(f"Created temporary PDF: {temp_pdf_path}")
            return temp_pdf_path
        else:
            # Clean up failed temp file safely (local helper)
            try:
                import os
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            except Exception:
                pass
            logging.error(f"Failed to convert {input_path} to PDF: {result['error']}")
            return None
            
    except Exception as e:
        logging.error(f"Error creating temporary PDF for {input_path}: {e}")
        return None