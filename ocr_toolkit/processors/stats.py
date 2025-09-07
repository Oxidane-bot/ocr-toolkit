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
    for OCR and other document processing methods.
    """
    total_processed: int = 0
    successful_processed: int = 0
    failed_processed: int = 0
    total_processing_time: float = 0.0
    method_stats: Dict[str, int] = field(default_factory=dict)
    
    def add_result(self, method: str, success: bool, processing_time: float = 0.0):
        """
        Add a processing result to the statistics.
        
        Args:
            method: Processing method used ('ocr', 'cnocr', etc.)
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
        
        return {
            'total_processed': self.total_processed,
            'successful_processed': self.successful_processed,
            'failed_processed': self.failed_processed,
            'success_rate': (self.successful_processed / self.total_processed) * 100,
            'average_time_per_file': self.total_processing_time / self.total_processed,
            'total_processing_time': self.total_processing_time,
            'method_stats': self.method_stats.copy()
        }
    
    def reset(self):
        """Reset all statistics to zero."""
        self.total_processed = 0
        self.successful_processed = 0
        self.failed_processed = 0
        self.total_processing_time = 0.0
        self.method_stats.clear()