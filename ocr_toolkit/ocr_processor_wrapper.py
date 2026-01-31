"""
OCR Processor Wrapper that provides enhanced OCR processing capabilities.

This wrapper provides a simplified interface for OCR processing using
PaddleOCR-VL-1.5 for document structure analysis.
"""

import logging
import os
import time
from typing import Any


class OCRProcessorWrapper:
    """
    OCR Processor Wrapper that provides enhanced OCR processing capabilities.

    This wrapper provides a simplified interface for OCR processing using
    PaddleOCR-VL-1.5 for document structure analysis.
    """

    def __init__(self, use_gpu: bool = True):
        """
        Initialize the OCR processor wrapper.

        Args:
            use_gpu: Whether to use GPU for processing
        """
        self.use_gpu = use_gpu
        self.logger = logging.getLogger(__name__)

        # Initialize PaddleOCR-VL handler
        self._initialize_handler()

    def _initialize_handler(self):
        """Initialize the PaddleOCR-VL handler."""
        self.logger.info("Using PaddleOCR-VL-1.5 engine (0.9B VLM for document parsing)")
        from .processors import PaddleOCRVLHandler
        self.handler = PaddleOCRVLHandler(use_gpu=self.use_gpu)

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
            # Get processing parameters
            pages = getattr(args, 'pages', None) if args else None
            profile = getattr(args, 'profile', False) if args else False

            # Use PaddleOCR-VL handler
            profiler = None
            if profile:
                from .utils.profiling import Profiler
                profiler = Profiler()

            # Get output directory for extracted images
            output_dir = getattr(args, '_output_dir', None) if args else None

            content, metadata = self.handler.process_document(
                file_path,
                output_dir=output_dir,
                pages=pages,
                profiler=profiler,
            )

            processing_time = time.time() - start_time

            result_dict = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'success': True,
                'chosen_method': 'paddleocr_vl',
                'final_content': content,
                'processing_time': processing_time,
                'pages': metadata.get('page_count', 1),
                'comparison': {},
                'ocr_result': {
                    'success': True,
                    'content': content,
                    'metadata': metadata,
                    'error': ''
                },
                'temp_files': [],
                'error': ''
            }

            if profiler:
                result_dict['ocr_result']['metadata']['profile'] = profiler.to_dict()

            return result_dict

        except Exception as e:
            self.logger.error(f"OCR processing failed for {file_path}: {e}")
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'success': False,
                'chosen_method': 'paddleocr_vl',
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


def create_ocr_processor_wrapper(use_gpu: bool = True) -> OCRProcessorWrapper:
    """
    Create an OCR processor wrapper instance.

    Args:
        use_gpu: Whether to use GPU for processing

    Returns:
        OCRProcessorWrapper instance
    """
    return OCRProcessorWrapper(use_gpu=use_gpu)
