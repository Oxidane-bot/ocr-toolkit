"""
MarkItDown processor implementation using the abstract base class.

This module provides a clean, reusable MarkItDown processor that follows
the FileProcessorBase interface for consistent behavior.
"""

import time
from typing import List
from pathlib import Path

from markitdown import MarkItDown

from .base import FileProcessorBase, ProcessingResult


class MarkItDownProcessor(FileProcessorBase):
    """
    MarkItDown processor implementation.
    
    This processor handles document conversion using MarkItDown library
    with proper error handling and format validation.
    """
    
    def __init__(self):
        """Initialize MarkItDown processor."""
        super().__init__()
        self.markitdown = MarkItDown()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats for MarkItDown processing."""
        return [
            # Office documents
            '.docx', '.pptx', '.xlsx', '.doc', '.ppt', '.xls',
            # PDF documents
            '.pdf',
            # Text documents
            '.txt', '.md', '.html', '.htm', '.rtf',
            # OpenDocument formats
            '.odt', '.odp', '.ods',
            # Data formats
            '.csv', '.tsv', '.json', '.xml',
            # E-books
            '.epub'
        ]
    
    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        ext = file_extension.lower()
        
        # MarkItDown doesn't support direct image processing
        image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
        if ext in image_formats:
            return False
            
        return ext in self.get_supported_formats()
    
    def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """
        Process document with MarkItDown.
        
        Args:
            file_path: Path to the document
            **kwargs: Additional processing parameters
            
        Returns:
            ProcessingResult object with processing results
        """
        start_time = time.time()
        result = self._create_result(file_path, 'markitdown', start_time)
        
        if not self._validate_file(file_path):
            result.error = f'Invalid file: {file_path}'
            result.processing_time = time.time() - start_time
            return result
        
        try:
            ext = Path(file_path).suffix.lower()
            
            if not self.supports_format(ext):
                result.error = f'MarkItDown does not support file format: {ext}'
                result.processing_time = time.time() - start_time
                return result
            
            # Process with MarkItDown
            markdown_result = self.markitdown.convert(file_path)
            result.content = markdown_result.text_content
            result.success = True
            
            self.logger.debug(f"MarkItDown processed {file_path} successfully")
            
        except Exception as e:
            return self._handle_exception(e, result)
        
        result.processing_time = time.time() - start_time
        return result