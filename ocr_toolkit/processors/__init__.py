"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .ocr_processor import OCRProcessor
from .factory import ProcessorFactory, get_processor_factory

__all__ = ['FileProcessorBase', 'ProcessingResult', 'OCRProcessor', 'ProcessorFactory', 'get_processor_factory']