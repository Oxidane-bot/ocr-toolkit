"""
Unit tests for processing statistics module.
"""

import pytest
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.processors.stats import ProcessingStats


class TestProcessingStats:
    """Test cases for ProcessingStats class."""
    
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.stats = ProcessingStats()
        
    def test_init(self):
        """Test ProcessingStats initialization."""
        assert self.stats.total_processed == 0
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 0
        assert self.stats.total_processing_time == 0.0
        assert len(self.stats.method_stats) == 0
        
    def test_add_result_ocr_success(self):
        """Test adding successful OCR result."""
        self.stats.add_result('ocr', True, 2.0)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.total_processing_time == 2.0
        assert self.stats.method_stats['ocr'] == 1
        
    def test_add_result_cnocr_success(self):
        """Test adding successful CnOCR result."""
        self.stats.add_result('cnocr', True, 1.5)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.total_processing_time == 1.5
        assert self.stats.method_stats['cnocr'] == 1
        
    def test_add_result_failure(self):
        """Test adding failed result."""
        self.stats.add_result('ocr', False, 0.5)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 1
        assert self.stats.total_processing_time == 0.5
        assert self.stats.method_stats['ocr'] == 1
        
    def test_get_summary_empty(self):
        """Test getting summary with no processing data."""
        summary = self.stats.get_summary()
        
        assert summary['total_processed'] == 0
        assert summary['success_rate'] == 0.0
        assert summary['average_time_per_file'] == 0.0
        assert len(summary['method_stats']) == 0
        
    def test_get_summary_with_data(self):
        """Test getting summary with processing data."""
        # Add some results
        self.stats.add_result('ocr', True, 1.0)
        self.stats.add_result('cnocr', True, 2.0)
        self.stats.add_result('ocr', True, 1.5)
        self.stats.add_result('ocr', False, 0.5)
        
        summary = self.stats.get_summary()
        
        assert summary['total_processed'] == 4
        assert summary['successful_processed'] == 3
        assert summary['failed_processed'] == 1
        assert summary['success_rate'] == 75.0  # 3/4 * 100
        assert summary['average_time_per_file'] == 1.25  # 5.0/4
        assert summary['total_processing_time'] == 5.0
        assert summary['method_stats']['ocr'] == 3
        assert summary['method_stats']['cnocr'] == 1
        
    def test_multiple_add_result_calls(self):
        """Test multiple sequential add_result calls."""
        self.stats.add_result('ocr', True, 1.0)
        self.stats.add_result('cnocr', True, 2.0)
        self.stats.add_result('ocr', False, 0.5)
        
        assert self.stats.total_processed == 3
        assert self.stats.successful_processed == 2
        assert self.stats.failed_processed == 1
        assert self.stats.total_processing_time == 3.5
        assert self.stats.method_stats['ocr'] == 2
        assert self.stats.method_stats['cnocr'] == 1
        
    def test_mixed_methods(self):
        """Test mixing different processing methods."""
        self.stats.add_result('ocr', True, 1.0)
        self.stats.add_result('cnocr', True, 2.0)
        self.stats.add_result('custom_method', True, 1.5)
        
        assert self.stats.total_processed == 3
        assert self.stats.successful_processed == 3
        assert self.stats.method_stats['ocr'] == 1
        assert self.stats.method_stats['cnocr'] == 1
        assert self.stats.method_stats['custom_method'] == 1
        
    def test_reset(self):
        """Test resetting statistics."""
        # Add some data
        self.stats.add_result('ocr', True, 1.0)
        self.stats.add_result('cnocr', True, 2.0)
        
        # Reset
        self.stats.reset()
        
        assert self.stats.total_processed == 0
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 0
        assert self.stats.total_processing_time == 0.0
        assert len(self.stats.method_stats) == 0
        
    def test_same_method_multiple_times(self):
        """Test adding results for the same method multiple times."""
        self.stats.add_result('ocr', True, 1.0)
        self.stats.add_result('ocr', False, 0.5)
        self.stats.add_result('ocr', True, 1.5)
        
        assert self.stats.total_processed == 3
        assert self.stats.successful_processed == 2
        assert self.stats.failed_processed == 1
        assert self.stats.method_stats['ocr'] == 3
        assert self.stats.total_processing_time == 3.0