"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .document_loader import DocumentLoader
from .excel_processor import ExcelDataProcessor
from .paddleocr_vl_handler import PaddleOCRVLHandler
from .text_file_processor import TextFileProcessor

__all__ = [
    'FileProcessorBase',
    'ProcessingResult',
    'PaddleOCRVLHandler',
    'DocumentLoader',
    'ExcelDataProcessor',
    'TextFileProcessor',
]
