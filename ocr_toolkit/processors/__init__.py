"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .cnocr_handler import CnOCRHandler
from .document_loader import DocumentLoader
from .factory import ProcessorFactory, get_processor_factory
from .ocr_processor import OCRProcessor
from .text_file_processor import TextFileProcessor

__all__ = [
    'FileProcessorBase',
    'ProcessingResult',
    'OCRProcessor',
    'ProcessorFactory',
    'get_processor_factory',
    'CnOCRHandler',
    'DocumentLoader',
    'TextFileProcessor',
]
