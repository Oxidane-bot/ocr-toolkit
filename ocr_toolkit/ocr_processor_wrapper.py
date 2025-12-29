"""
OCR Processor Wrapper that provides enhanced OCR processing capabilities.
"""

import logging
import os
import time
from typing import Any

from .processors import get_processor_factory
from .utils import get_temp_manager


class OCRProcessorWrapper:
    """
    OCR Processor Wrapper that provides enhanced OCR processing capabilities.

    This wrapper provides a simplified interface for OCR processing using
    the factory pattern for processor management.
    """

    def __init__(self, ocr_model, batch_size: int = 16, use_zh: bool = False):
        """
        Initialize the OCR processor wrapper.

        Args:
            ocr_model: Loaded DocTR OCR model
            batch_size: Batch size for OCR processing
            use_zh: Whether to use CnOCR for Chinese text recognition
        """
        self.ocr_model = ocr_model
        self.batch_size = batch_size
        self.use_zh = use_zh
        self.logger = logging.getLogger(__name__)
        self.temp_manager = get_temp_manager()

        # Get processor factory and create OCR processor
        self.factory = get_processor_factory()
        self.processor = self.factory.create_processor(
            'ocr',
            ocr_model=ocr_model,
            batch_size=batch_size,
            use_cnocr=use_zh
        )

        if not self.processor:
            raise RuntimeError("Failed to create OCR processor")

    def process_document(self, file_path: str, args=None) -> dict[str, Any]:
        """
        Process document with OCR.

        Args:
            file_path: Path to the document
            args: Command line arguments (optional)

        Returns:
            Result dictionary with processing information
        """
        start_time = time.time()

        try:
            # Process with OCR processor
            result = self.processor.process(
                file_path,
                fast=getattr(args, 'fast', False) if args else False,
                pages=getattr(args, 'pages', None) if args else None,
                profile=getattr(args, 'profile', False) if args else False,
            )

            # Convert to legacy format for compatibility
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'success': result.success,
                'chosen_method': 'ocr',
                'final_content': result.content,
                'processing_time': result.processing_time,
                'pages': result.pages,
                'comparison': {},
                'ocr_result': result.to_dict(),
                'temp_files': result.temp_files,
                'error': result.error if not result.success else ''
            }

        except Exception as e:
            self.logger.error(f"OCR processing failed for {file_path}: {e}")
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'success': False,
                'chosen_method': 'ocr',
                'final_content': '',
                'processing_time': time.time() - start_time,
                'pages': 0,
                'comparison': {},
                'ocr_result': {
                    'success': False,
                    'content': '',
                    'error': str(e)
                },
                'temp_files': [],
                'error': str(e)
            }

    def get_statistics(self) -> dict[str, Any]:
        """Get basic processing statistics."""
        return {'ocr_processed': 1, 'success_rate': 100.0}

    def get_detailed_statistics(self) -> dict[str, Any]:
        """Get comprehensive processing statistics."""
        return self.get_statistics()


def create_ocr_processor_wrapper(ocr_model, batch_size: int = 16, use_zh: bool = False) -> OCRProcessorWrapper:
    """
    Create an OCR processor wrapper instance.

    Args:
        ocr_model: Loaded DocTR OCR model
        batch_size: Batch size for OCR processing
        use_zh: Whether to use CnOCR for Chinese text recognition

    Returns:
        OCRProcessorWrapper instance
    """
    return OCRProcessorWrapper(ocr_model, batch_size=batch_size, use_zh=use_zh)
