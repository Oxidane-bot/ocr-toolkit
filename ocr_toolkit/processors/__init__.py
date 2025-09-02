"""
Processor module for document processing interfaces and implementations.
"""

from .base import FileProcessorBase, ProcessingResult
from .ocr_processor import OCRProcessor

__all__ = ['FileProcessorBase', 'ProcessingResult', 'OCRProcessor']