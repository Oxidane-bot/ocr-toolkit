"""
OCR processor implementation using the abstract base class.

This module provides a clean, reusable OCR processor that follows
the FileProcessorBase interface for consistent behavior.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from doctr.io import DocumentFile

from .base import FileProcessorBase, ProcessingResult
from ..converters import get_office_converter
from ..temp_file_manager import cleanup_temp_files


class OCRProcessor(FileProcessorBase):
    """
    OCR processor implementation using DocTR.
    
    This processor handles OCR processing for PDFs, images, and Office documents
    with proper temporary file management and error handling.
    """
    
    def __init__(self, ocr_model, batch_size: int = 16):
        """
        Initialize OCR processor.
        
        Args:
            ocr_model: Loaded DocTR OCR model
            batch_size: Number of pages to process in each batch
        """
        super().__init__()
        self.ocr_model = ocr_model
        self.batch_size = batch_size
        self.office_converter = get_office_converter()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats for OCR processing."""
        return [
            # PDF files
            '.pdf',
            # Image files
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif',
            # Office documents (converted to PDF first)
            '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'
        ]
    
    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        return file_extension.lower() in self.get_supported_formats()
    
    def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """
        Process document with OCR.
        
        Args:
            file_path: Path to the document
            **kwargs: Additional processing parameters
            
        Returns:
            ProcessingResult object with processing results
        """
        start_time = time.time()
        result = self._create_result(file_path, 'ocr', start_time)
        
        if not self._validate_file(file_path):
            result.error = f'Invalid file: {file_path}'
            result.processing_time = time.time() - start_time
            return result
        
        try:
            ext = Path(file_path).suffix.lower()
            
            if not self.supports_format(ext):
                result.error = f'Unsupported file format for OCR: {ext}'
                result.processing_time = time.time() - start_time
                return result
            
            # Load document based on format
            doc = self._load_document(file_path, ext, result)
            if doc is None:
                result.processing_time = time.time() - start_time
                return result
            
            # Process with OCR
            content = self._process_with_ocr(doc, file_path, ext)
            
            result.content = content
            result.success = True
            
            self.logger.debug(f"OCR processed {file_path} successfully")
            
        except Exception as e:
            return self._handle_exception(e, result)
        
        finally:
            # Clean up temporary files
            if result.temp_files:
                cleanup_temp_files(result.temp_files)
        
        result.processing_time = time.time() - start_time
        return result
    
    def _load_document(self, file_path: str, ext: str, result: ProcessingResult) -> Optional[DocumentFile]:
        """
        Load document file for OCR processing.
        
        Args:
            file_path: Path to the document
            ext: File extension
            result: Result object to update with temp files
            
        Returns:
            DocumentFile object or None if loading failed
        """
        try:
            if ext == '.pdf':
                # Direct PDF processing
                doc = DocumentFile.from_pdf(file_path)
                self.logger.debug(f"OCR loaded PDF with {len(doc)} pages")
                return doc
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
                # Direct image processing
                doc = DocumentFile.from_images([file_path])
                self.logger.debug(f"OCR loaded image for processing")
                return doc
                
            elif ext in ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']:
                # Office document - convert to PDF first
                temp_pdf = self.office_converter.create_temp_pdf(file_path)
                if temp_pdf:
                    result.temp_files.append(temp_pdf)
                    doc = DocumentFile.from_pdf(temp_pdf)
                    self.logger.debug(f"OCR converted Office document to PDF with {len(doc)} pages")
                    return doc
                else:
                    result.error = f'Failed to convert Office document {file_path} to PDF'
                    return None
            
            return None
            
        except Exception as e:
            result.error = f'Failed to load document for OCR: {str(e)}'
            return None
    
    def _process_with_ocr(self, doc: DocumentFile, file_path: str, ext: str) -> str:
        """
        Process loaded document with OCR model.
        
        Args:
            doc: Loaded DocumentFile
            file_path: Original file path
            ext: File extension
            
        Returns:
            Processed markdown content
        """
        markdown_content = []
        
        # Process in batches
        for i in range(0, len(doc), self.batch_size):
            batch = doc[i : i + self.batch_size]
            ocr_result = self.ocr_model(batch)
            
            for page_idx, page_result in enumerate(ocr_result.pages):
                current_page_number = i + page_idx + 1
                text = page_result.render()
                
                # Format content based on file type
                if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
                    # For single images, use filename as header
                    markdown_content.append(f"# {os.path.basename(file_path)}\n\n{text}")
                else:
                    # For multi-page documents, use page numbers
                    markdown_content.append(f"## Page {current_page_number}\n\n{text}")
        
        return "\n\n".join(markdown_content)