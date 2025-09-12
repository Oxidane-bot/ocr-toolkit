"""
Processor factory for creating and managing document processors.

This module provides a factory pattern for creating different types of
document processors based on file formats and processing requirements.
"""

import logging
from typing import Dict, Type, Optional, Any
from pathlib import Path

from .base import FileProcessorBase
from ..config import get_all_supported_formats


class ProcessorFactory:
    """
    Simplified factory for creating OCR processors.
    
    This factory creates OCR processors with minimal overhead,
    focusing on the primary use case of OCR document processing.
    """
    
    def __init__(self):
        """Initialize the processor factory."""
        self._ocr_processor_class: Optional[Type[FileProcessorBase]] = None
        self.logger = logging.getLogger(__name__)
        self._register_ocr_processor()
    
    def _register_ocr_processor(self) -> None:
        """Register the OCR processor class."""
        try:
            from .ocr_processor import OCRProcessor
            self._ocr_processor_class = OCRProcessor
            self.logger.debug("Registered OCR processor")
        except ImportError as e:
            self.logger.error(f"Could not register OCR processor: {e}")
    
    def create_ocr_processor(self, **kwargs) -> Optional[FileProcessorBase]:
        """
        Create an OCR processor instance.
        
        Args:
            **kwargs: Arguments to pass to the OCR processor constructor
            
        Returns:
            OCR processor instance or None if creation failed
        """
        if not self._ocr_processor_class:
            self.logger.error("OCR processor class not available")
            return None
        
        try:
            processor = self._ocr_processor_class(**kwargs)
            self.logger.debug("Created OCR processor")
            return processor
        except Exception as e:
            self.logger.error(f"Failed to create OCR processor: {e}")
            return None
    
    def create_processor(self, processor_type: str, **kwargs) -> Optional[FileProcessorBase]:
        """
        Create a processor instance (backward compatibility).
        
        Args:
            processor_type: Type of processor ('ocr' is the only supported type)
            **kwargs: Additional arguments to pass to the processor constructor
            
        Returns:
            Processor instance or None if type not supported
        """
        if processor_type == 'ocr':
            return self.create_ocr_processor(**kwargs)
        
        self.logger.error(f"Unsupported processor type: {processor_type}")
        return None
    
    def get_processor_for_file(self, file_path: str, **kwargs) -> Optional[FileProcessorBase]:
        """
        Get the OCR processor for any supported file.
        
        Args:
            file_path: Path to the file to process
            **kwargs: Additional arguments for processor creation
            
        Returns:
            OCR processor instance or None if file format not supported
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Check if file is supported by OCR
        from ..config import get_ocr_supported_formats
        if file_ext in get_ocr_supported_formats():
            return self.create_ocr_processor(**kwargs)
        
        self.logger.warning(f"Unsupported file format: {file_ext}")
        return None
    
    def is_ocr_available(self) -> bool:
        """
        Check if OCR processor is available.
        
        Returns:
            True if OCR processor can be created, False otherwise
        """
        return self._ocr_processor_class is not None


# Global factory instance
_global_factory = None


def get_processor_factory() -> ProcessorFactory:
    """
    Get the global processor factory instance.
    
    Returns:
        Global ProcessorFactory instance
    """
    global _global_factory
    if _global_factory is None:
        _global_factory = ProcessorFactory()
    return _global_factory
