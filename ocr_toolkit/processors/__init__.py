"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .factory import ProcessorFactory, get_processor_factory
from .ocr_processor import OCRProcessor

__all__ = ['FileProcessorBase', 'ProcessingResult', 'OCRProcessor', 'ProcessorFactory', 'get_processor_factory']
