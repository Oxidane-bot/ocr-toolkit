"""
Office document conversion module using strategy pattern.

This module provides a clean interface for converting Office documents to PDF
using different conversion strategies, improving maintainability and extensibility.
"""

import os
import time
import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class ConversionStrategy(ABC):
    """Abstract base class for Office document conversion strategies."""
    
    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Convert document using this strategy.
        
        Args:
            input_path: Path to input file
            output_path: Path to output PDF file
            
        Returns:
            Dictionary with conversion results
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.
        
        Args:
            file_extension: File extension (e.g., '.docx')
            
        Returns:
            True if supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_method_name(self) -> str:
        """Get the name of this conversion method."""
        pass


class DocxToPdfStrategy(ConversionStrategy):
    """Strategy for converting DOCX files using docx2pdf library."""
    
    def convert(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Convert DOCX to PDF using docx2pdf library."""
        result = {
            'method': self.get_method_name(),
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
    
    def supports_format(self, file_extension: str) -> bool:
        """Supports only .docx files."""
        return file_extension.lower() == '.docx'
    
    def get_method_name(self) -> str:
        return 'docx2pdf'


class WordComStrategy(ConversionStrategy):
    """Strategy for converting Word documents using COM automation."""
    
    def convert(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Convert Word document to PDF using Word COM automation."""
        result = {
            'method': self.get_method_name(),
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
    
    def supports_format(self, file_extension: str) -> bool:
        """Supports Word document formats."""
        return file_extension.lower() in ['.doc', '.docx']
    
    def get_method_name(self) -> str:
        return 'word_com'


class PowerPointComStrategy(ConversionStrategy):
    """Strategy for converting PowerPoint presentations using COM automation."""
    
    def convert(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Convert PowerPoint presentation to PDF using PowerPoint COM automation."""
        result = {
            'method': self.get_method_name(),
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
    
    def supports_format(self, file_extension: str) -> bool:
        """Supports PowerPoint formats."""
        return file_extension.lower() in ['.ppt', '.pptx']
    
    def get_method_name(self) -> str:
        return 'powerpoint_com'


class ExcelComStrategy(ConversionStrategy):
    """Strategy for converting Excel workbooks using COM automation."""
    
    def convert(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Convert Excel workbook to PDF using Excel COM automation."""
        result = {
            'method': self.get_method_name(),
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
    
    def supports_format(self, file_extension: str) -> bool:
        """Supports Excel formats."""
        return file_extension.lower() in ['.xls', '.xlsx']
    
    def get_method_name(self) -> str:
        return 'excel_com'


class OfficeConverter:
    """
    Office document converter using strategy pattern.
    
    This class provides a clean interface for converting Office documents to PDF
    by automatically selecting the appropriate conversion strategy.
    """
    
    def __init__(self):
        """Initialize converter with available strategies."""
        self.strategies = [
            DocxToPdfStrategy(),
            WordComStrategy(), 
            PowerPointComStrategy(),
            ExcelComStrategy()
        ]
    
    def convert_to_pdf(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Convert Office document to PDF using the appropriate strategy.
        
        Args:
            input_path: Path to input Office file
            output_path: Path to output PDF file
            
        Returns:
            Dictionary with conversion results
        """
        ext = Path(input_path).suffix.lower()
        
        # For .docx files, try docx2pdf first, then fall back to COM
        if ext == '.docx':
            # Try docx2pdf first (faster)
            docx_strategy = next(s for s in self.strategies if isinstance(s, DocxToPdfStrategy))
            result = docx_strategy.convert(input_path, output_path)
            
            if not result['success']:
                logging.warning("docx2pdf failed, trying Word COM automation")
                word_strategy = next(s for s in self.strategies if isinstance(s, WordComStrategy))
                result = word_strategy.convert(input_path, output_path)
            
            return result
        
        # For other formats, find the appropriate strategy
        for strategy in self.strategies:
            if strategy.supports_format(ext):
                return strategy.convert(input_path, output_path)
        
        # No strategy found
        return {
            'method': 'unsupported',
            'success': False,
            'processing_time': 0,
            'error': f'Unsupported file format: {ext}'
        }
    
    def create_temp_pdf(self, input_path: str) -> Optional[str]:
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
            result = self.convert_to_pdf(input_path, temp_pdf_path)
            
            if result['success']:
                logging.info(f"Created temporary PDF: {temp_pdf_path}")
                return temp_pdf_path
            else:
                # Clean up failed temp file safely
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
    
    def get_supported_formats(self) -> list[str]:
        """
        Get list of all supported file formats.
        
        Returns:
            List of supported file extensions
        """
        formats = set()
        for strategy in self.strategies:
            if isinstance(strategy, DocxToPdfStrategy):
                formats.add('.docx')
            elif isinstance(strategy, WordComStrategy):
                formats.update(['.doc', '.docx'])
            elif isinstance(strategy, PowerPointComStrategy):
                formats.update(['.ppt', '.pptx'])
            elif isinstance(strategy, ExcelComStrategy):
                formats.update(['.xls', '.xlsx'])
        
        return sorted(list(formats))


# Singleton instance for global use
_office_converter = None


def get_office_converter() -> OfficeConverter:
    """Get the global Office converter instance."""
    global _office_converter
    if _office_converter is None:
        _office_converter = OfficeConverter()
    return _office_converter


# Backward compatibility functions
def convert_office_to_pdf(input_path: str, output_path: str) -> Dict[str, Any]:
    """Convert Office document to PDF (backward compatibility)."""
    return get_office_converter().convert_to_pdf(input_path, output_path)


def create_temp_pdf(input_path: str) -> Optional[str]:
    """Create temporary PDF from Office document (backward compatibility)."""
    return get_office_converter().create_temp_pdf(input_path)