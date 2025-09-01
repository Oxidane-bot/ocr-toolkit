"""
Dual processor module for intelligent document processing.

This module orchestrates both MarkItDown and OCR processing, automatically
selecting the best result based on quality evaluation.
"""

import os
import time
import logging
import concurrent.futures
from typing import Dict, Any, Optional

from .processors.base import ProcessingResult
from .processors.stats import ProcessingStats
from .processors.ocr_processor import OCRProcessor
from .processors.markitdown_processor import MarkItDownProcessor
from .quality_evaluator import QualityEvaluator
from .temp_file_manager import cleanup_temp_files


class DualProcessor:
    """
    Processes documents using both MarkItDown and OCR, selecting the best result.
    
    This processor implements intelligent dual-path processing with quality evaluation
    and automatic method selection for optimal results.
    """
    
    def __init__(self, ocr_model, quality_evaluator: Optional[QualityEvaluator] = None, batch_size: int = 16):
        """
        Initialize the dual processor.
        
        Args:
            ocr_model: Loaded DocTR OCR model
            quality_evaluator: Quality evaluator instance (optional)
            batch_size: Batch size for OCR processing
        """
        self.quality_evaluator = quality_evaluator or QualityEvaluator()
        self.stats = ProcessingStats()
        
        # Initialize specialized processors
        self.ocr_processor = OCRProcessor(ocr_model, batch_size)
        self.markitdown_processor = MarkItDownProcessor()
    
    def process_document_dual(self, file_path: str, args) -> Dict[str, Any]:
        """
        Process document with both MarkItDown and OCR, selecting the best result.
        
        Args:
            file_path: Path to the document
            args: Command line arguments (for backward compatibility)
            
        Returns:
            Combined result with chosen method (backward compatibility format)
        """
        total_start_time = time.time()
        
        # Legacy result format for backward compatibility
        result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'success': False,
            'chosen_method': 'none',
            'final_content': '',
            'processing_time': 0,
            'comparison': {},
            'markitdown_result': {},
            'ocr_result': {},
            'temp_files': []
        }
        
        try:
            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both processing jobs
                future_md = executor.submit(self.markitdown_processor.process, file_path)
                future_ocr = executor.submit(self.ocr_processor.process, file_path)
                
                # Wait for both to complete
                markitdown_result = future_md.result()
                ocr_result = future_ocr.result()
            
            # Convert ProcessingResult objects to legacy format
            md_legacy = markitdown_result.to_dict()
            ocr_legacy = ocr_result.to_dict()
            
            result['markitdown_result'] = md_legacy
            result['ocr_result'] = ocr_legacy
            
            # Collect temp files for cleanup
            result['temp_files'].extend(ocr_result.temp_files)
            
            # Compare results and choose the best one
            comparison = self.quality_evaluator.compare_results(
                md_legacy, ocr_legacy, file_path
            )
            result['comparison'] = comparison
            
            # Set final result based on comparison
            chosen_method = comparison['chosen_method']
            result['chosen_method'] = chosen_method
            
            if chosen_method == 'markitdown':
                result['final_content'] = markitdown_result.content
                result['success'] = markitdown_result.success
            elif chosen_method == 'ocr':
                result['final_content'] = ocr_result.content
                result['success'] = ocr_result.success
            else:
                result['success'] = False
            
            # Update statistics using new ProcessingStats
            self.stats.add_dual_result(
                chosen_method=chosen_method,
                markitdown_available=comparison['markitdown_available'],
                ocr_available=comparison['ocr_available'],
                processing_time=0  # Will be set below
            )
                
        except Exception as e:
            result['error'] = str(e)
            logging.error(f"Dual processing failed for {file_path}: {e}")
        
        finally:
            # Clean up temporary files
            cleanup_temp_files(result['temp_files'])
            result['processing_time'] = time.time() - total_start_time
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics in legacy format for backward compatibility."""
        return self.stats.get_legacy_dict()
    
    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        return self.stats.get_summary()


def create_dual_processor(ocr_model, batch_size: int = 16) -> DualProcessor:
    """Factory function to create a dual processor instance."""
    return DualProcessor(ocr_model, batch_size=batch_size)