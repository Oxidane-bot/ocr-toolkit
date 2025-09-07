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
    Factory class for creating document processors.
    
    This factory manages the creation of different processor types
    and handles processor selection based on file formats and requirements.
    """
    
    def __init__(self):
        """Initialize the processor factory."""
        self._processors: Dict[str, Type[FileProcessorBase]] = {}
        self._processor_instances: Dict[str, FileProcessorBase] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_processor(self, processor_type: str, processor_class: Type[FileProcessorBase]) -> None:
        """
        Register a processor class with the factory.
        
        Args:
            processor_type: Unique identifier for the processor type
            processor_class: The processor class to register
        """
        self._processors[processor_type] = processor_class
        self.logger.debug(f"Registered processor: {processor_type}")
    
    def create_processor(self, processor_type: str, **kwargs) -> Optional[FileProcessorBase]:
        """
        Create a processor instance of the specified type.
        
        Args:
            processor_type: Type of processor to create
            **kwargs: Additional arguments to pass to the processor constructor
            
        Returns:
            Processor instance or None if type not found
        """
        if processor_type not in self._processors:
            self.logger.error(f"Unknown processor type: {processor_type}")
            return None
        
        try:
            processor_class = self._processors[processor_type]
            processor = processor_class(**kwargs)
            self.logger.debug(f"Created processor: {processor_type}")
            return processor
        except Exception as e:
            self.logger.error(f"Failed to create processor {processor_type}: {e}")
            return None
    
    def get_or_create_processor(self, processor_type: str, **kwargs) -> Optional[FileProcessorBase]:
        """
        Get existing processor instance or create a new one.
        
        Args:
            processor_type: Type of processor to get/create
            **kwargs: Additional arguments for processor creation
            
        Returns:
            Processor instance or None if creation failed
        """
        # Create cache key based on processor type and kwargs
        cache_key = f"{processor_type}_{hash(frozenset(kwargs.items()))}"
        
        if cache_key not in self._processor_instances:
            processor = self.create_processor(processor_type, **kwargs)
            if processor:
                self._processor_instances[cache_key] = processor
            else:
                return None
        
        return self._processor_instances[cache_key]
    
    def get_processor_for_file(self, file_path: str, **kwargs) -> Optional[FileProcessorBase]:
        """
        Get the appropriate processor for a file based on its extension.
        
        Args:
            file_path: Path to the file to process
            **kwargs: Additional arguments for processor selection/creation
            
        Returns:
            Appropriate processor or None if no suitable processor found
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Check if file is supported
        if file_ext not in get_all_supported_formats():
            self.logger.warning(f"Unsupported file format: {file_ext}")
            return None
        
        # Try to find appropriate processor
        # This is a simplified implementation - can be extended with more sophisticated logic
        
        # OCR processor for images, PDFs, and Office documents
        from ..config import get_ocr_supported_formats
        if file_ext in get_ocr_supported_formats():
            return self.get_or_create_processor('ocr', **kwargs)
        
        # MarkItDown processor for other supported formats
        from ..config import get_markitdown_supported_formats
        if file_ext in get_markitdown_supported_formats():
            return self.get_or_create_processor('markitdown', **kwargs)
        
        self.logger.warning(f"No suitable processor found for file: {file_path}")
        return None
    
    def list_processors(self) -> Dict[str, Type[FileProcessorBase]]:
        """
        Get a dictionary of all registered processors.
        
        Returns:
            Dictionary mapping processor types to their classes
        """
        return self._processors.copy()
    
    def clear_cache(self) -> None:
        """Clear all cached processor instances."""
        self._processor_instances.clear()
        self.logger.debug("Cleared processor cache")
    
    def get_processor_info(self, processor_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered processor.
        
        Args:
            processor_type: Type of processor to get info for
            
        Returns:
            Dictionary with processor information or None if not found
        """
        if processor_type not in self._processors:
            return None
        
        processor_class = self._processors[processor_type]
        
        # Try to get supported formats from the class
        supported_formats = []
        try:
            # Create a temporary instance to get supported formats
            temp_instance = processor_class()
            supported_formats = temp_instance.get_supported_formats()
        except Exception as e:
            self.logger.debug(f"Could not get supported formats for {processor_type}: {e}")
        
        return {
            'type': processor_type,
            'class': processor_class.__name__,
            'module': processor_class.__module__,
            'supported_formats': supported_formats,
            'docstring': processor_class.__doc__
        }


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
        _register_default_processors(_global_factory)
    return _global_factory


def _register_default_processors(factory: ProcessorFactory) -> None:
    """
    Register default processors with the factory.
    
    Args:
        factory: ProcessorFactory instance to register processors with
    """
    try:
        # Register OCR processor
        from .ocr_processor import OCRProcessor
        factory.register_processor('ocr', OCRProcessor)
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Could not register OCR processor: {e}")
    
    # MarkItDown processor has been removed - we now focus on OCR only