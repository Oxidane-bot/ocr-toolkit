"""
Processing statistics tracking module.

This module provides a dedicated class for tracking processing statistics,
separating this concern from the main processing logic.
"""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class ProcessingStats:
    """
    Tracks statistics for document processing operations.
    
    This class provides a centralized way to track processing metrics
    across different processors and processing modes.
    """
    total_processed: int = 0
    successful_processed: int = 0
    failed_processed: int = 0
    markitdown_chosen: int = 0
    ocr_chosen: int = 0
    markitdown_only: int = 0
    ocr_only: int = 0
    both_failed: int = 0
    total_processing_time: float = 0.0
    method_stats: Dict[str, int] = field(default_factory=dict)
    
    def add_result(self, method: str, success: bool, processing_time: float = 0.0):
        """
        Add a processing result to the statistics.
        
        Args:
            method: Processing method used ('markitdown', 'ocr', etc.)
            success: Whether processing was successful
            processing_time: Time taken for processing
        """
        self.total_processed += 1
        self.total_processing_time += processing_time
        
        if success:
            self.successful_processed += 1
        else:
            self.failed_processed += 1
        
        # Track method-specific statistics
        if method in self.method_stats:
            self.method_stats[method] += 1
        else:
            self.method_stats[method] = 1
            
        # Track specific method choices for dual processing
        if method == 'markitdown':
            self.markitdown_chosen += 1
        elif method == 'ocr':
            self.ocr_chosen += 1
    
    def add_dual_result(self, chosen_method: str, markitdown_available: bool, 
                       ocr_available: bool, processing_time: float = 0.0):
        """
        Add a dual processing result to the statistics.
        
        Args:
            chosen_method: The method that was ultimately chosen
            markitdown_available: Whether MarkItDown processing succeeded
            ocr_available: Whether OCR processing succeeded
            processing_time: Total processing time for both methods
        """
        self.total_processed += 1
        self.total_processing_time += processing_time
        
        # Determine success based on chosen method
        success = chosen_method != 'none'
        if success:
            self.successful_processed += 1
            
            # Track method selection
            if chosen_method == 'markitdown':
                self.markitdown_chosen += 1
            elif chosen_method == 'ocr':
                self.ocr_chosen += 1
        else:
            self.failed_processed += 1
            self.both_failed += 1
        
        # Track availability patterns
        if markitdown_available and not ocr_available:
            self.markitdown_only += 1
        elif ocr_available and not markitdown_available:
            self.ocr_only += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of processing statistics.
        
        Returns:
            Dictionary with calculated statistics and percentages
        """
        if self.total_processed == 0:
            return {
                'total_processed': 0,
                'success_rate': 0.0,
                'average_time_per_file': 0.0,
                'method_stats': {}
            }
        
        summary = {
            'total_processed': self.total_processed,
            'successful_processed': self.successful_processed,
            'failed_processed': self.failed_processed,
            'success_rate': (self.successful_processed / self.total_processed) * 100,
            'average_time_per_file': self.total_processing_time / self.total_processed,
            'total_processing_time': self.total_processing_time,
            'method_stats': self.method_stats.copy()
        }
        
        # Add dual processing specific stats if relevant
        if self.markitdown_chosen > 0 or self.ocr_chosen > 0:
            summary.update({
                'markitdown_chosen': self.markitdown_chosen,
                'ocr_chosen': self.ocr_chosen,
                'markitdown_chosen_pct': (self.markitdown_chosen / self.total_processed) * 100,
                'ocr_chosen_pct': (self.ocr_chosen / self.total_processed) * 100,
                'markitdown_only': self.markitdown_only,
                'ocr_only': self.ocr_only,
                'both_failed': self.both_failed
            })
        
        return summary
    
    def get_legacy_dict(self) -> Dict[str, Any]:
        """
        Get statistics in the legacy dictionary format for backward compatibility.
        
        Returns:
            Dictionary matching the old statistics format
        """
        summary = self.get_summary()
        
        # Convert to legacy format
        legacy_stats = {
            'total_processed': self.total_processed,
            'markitdown_chosen': self.markitdown_chosen,
            'ocr_chosen': self.ocr_chosen,
            'markitdown_only': self.markitdown_only,
            'ocr_only': self.ocr_only,
            'both_failed': self.both_failed
        }
        
        # Add percentages if we have data
        if self.total_processed > 0:
            legacy_stats.update({
                'markitdown_chosen_pct': summary.get('markitdown_chosen_pct', 0),
                'ocr_chosen_pct': summary.get('ocr_chosen_pct', 0),
                'success_rate': summary['success_rate']
            })
        
        return legacy_stats
    
    def reset(self):
        """Reset all statistics to zero."""
        self.total_processed = 0
        self.successful_processed = 0
        self.failed_processed = 0
        self.markitdown_chosen = 0
        self.ocr_chosen = 0
        self.markitdown_only = 0
        self.ocr_only = 0
        self.both_failed = 0
        self.total_processing_time = 0.0
        self.method_stats.clear()