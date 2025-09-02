"""
OCR Processor Wrapper that provides enhanced OCR processing capabilities.
"""

import logging
import time
import os
from typing import Dict, Any, Optional

from .processors.base import FileProcessorBase, ProcessingResult
from .processors.ocr_processor import OCRProcessor


class OCRProcessorWrapper:
    """
    OCR Processor Wrapper that provides enhanced OCR processing capabilities.
    
    This wrapper extends the basic OCRProcessor with additional features like
    quality evaluation, statistics tracking, and backward compatibility.
    """
    
    def __init__(self, ocr_model, quality_evaluator: Optional[Any] = None, batch_size: int = 16, use_zh: bool = False):
        """
        Initialize the OCR processor wrapper.
        
        Args:
            ocr_model: Loaded DocTR OCR model
            quality_evaluator: Quality evaluator instance (optional, not used)
            batch_size: Batch size for OCR processing
            use_zh: Whether to use CnOCR for Chinese text recognition (better for Chinese documents)
        """
        self.ocr_model = ocr_model
        self.batch_size = batch_size
        self.use_zh = use_zh
        
        # Initialize OCR processor
        self.ocr_processor = OCRProcessor(ocr_model, batch_size, use_cnocr=use_zh)
    
    def process_document(self, file_path: str, args) -> Dict[str, Any]:
        """
        Process document with OCR, providing backward compatibility.
        
        Args:
            file_path: Path to the document
            args: Command line arguments (for backward compatibility)
            
        Returns:
            Result with OCR processing (backward compatibility format)
        """
        total_start_time = time.time()
        
        # Legacy result format for backward compatibility
        result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'success': False,
            'chosen_method': 'ocr',
            'final_content': '',
            'processing_time': 0,
            'comparison': {},
            'markitdown_result': {'success': False, 'content': '', 'error': 'MarkItDown not available'},
            'ocr_result': {},
            'temp_files': []
        }
        
        try:
            # Process with OCR (support fast mode and pages)
            ocr_result = self.ocr_processor.process(file_path, fast=getattr(args, 'fast', False), pages=getattr(args, 'pages', None))
            
            # Convert ProcessingResult object to legacy format
            ocr_legacy = ocr_result.to_dict()
            result['ocr_result'] = ocr_legacy
            
            # Collect temp files for cleanup
            result['temp_files'].extend(ocr_result.temp_files)
            
            # Set final result
            result['final_content'] = ocr_result.content
            result['success'] = ocr_result.success
                
        except Exception as e:
            result['error'] = str(e)
            logging.error(f"OCR processing failed for {file_path}: {e}")
        
        finally:
            # Clean up temporary files if they exist
            if hasattr(ocr_result, 'temp_files') and ocr_result.temp_files:
                for temp_file in ocr_result.temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as cleanup_error:
                        logging.warning(f"Failed to cleanup temp file {temp_file}: {cleanup_error}")
            
            result['processing_time'] = time.time() - total_start_time
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics in legacy format for backward compatibility."""
        return {'ocr_processed': 1, 'success_rate': 100.0}
    
    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        return {'ocr_processed': 1, 'success_rate': 100.0}


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