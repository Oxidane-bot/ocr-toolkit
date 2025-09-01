"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .ocr_processor import OCRProcessor
from .markitdown_processor import MarkItDownProcessor

__all__ = ['FileProcessorBase', 'ProcessingResult', 'OCRProcessor', 'MarkItDownProcessor']