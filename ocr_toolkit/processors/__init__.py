"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .document_loader import DocumentLoader
from .excel_processor import ExcelDataProcessor
from .factory import ProcessorFactory, get_processor_factory
from .ocr_processor import OCRProcessor
from .paddleocr_handler import PaddleOCRHandler
from .text_file_processor import TextFileProcessor

__all__ = [
    'FileProcessorBase',
    'ProcessingResult',
    'OCRProcessor',
    'ProcessorFactory',
    'get_processor_factory',
    'PaddleOCRHandler',
    'DocumentLoader',
    'ExcelDataProcessor',
    'TextFileProcessor',
]
