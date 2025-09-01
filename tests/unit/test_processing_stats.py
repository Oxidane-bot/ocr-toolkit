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
        assert self.stats.markitdown_chosen == 0
        assert self.stats.ocr_chosen == 0
        assert self.stats.markitdown_only == 0
        assert self.stats.ocr_only == 0
        assert self.stats.both_failed == 0
        assert self.stats.total_processing_time == 0.0
        assert len(self.stats.method_stats) == 0
        
    def test_add_result_markitdown_success(self):
        """Test adding successful MarkItDown result."""
        self.stats.add_result('markitdown', True, 1.5)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.markitdown_chosen == 1
        assert self.stats.ocr_chosen == 0
        assert self.stats.total_processing_time == 1.5
        assert self.stats.method_stats['markitdown'] == 1
        
    def test_add_result_ocr_success(self):
        """Test adding successful OCR result."""
        self.stats.add_result('ocr', True, 2.0)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.markitdown_chosen == 0
        assert self.stats.ocr_chosen == 1
        assert self.stats.total_processing_time == 2.0
        assert self.stats.method_stats['ocr'] == 1
        
    def test_add_result_failure(self):
        """Test adding failed result."""
        self.stats.add_result('markitdown', False, 0.5)
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 1
        assert self.stats.markitdown_chosen == 1  # Stats track all method usage, not just successes
        assert self.stats.ocr_chosen == 0
        assert self.stats.total_processing_time == 0.5
        assert self.stats.method_stats['markitdown'] == 1
        
    def test_add_dual_result_markitdown_chosen(self):
        """Test adding dual result with MarkItDown chosen."""
        self.stats.add_dual_result(
            chosen_method='markitdown',
            markitdown_available=True,
            ocr_available=True,
            processing_time=2.5
        )
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.markitdown_chosen == 1
        assert self.stats.ocr_chosen == 0
        assert self.stats.markitdown_only == 0
        assert self.stats.ocr_only == 0
        assert self.stats.both_failed == 0
        assert self.stats.total_processing_time == 2.5
        
    def test_add_dual_result_ocr_chosen(self):
        """Test adding dual result with OCR chosen."""
        self.stats.add_dual_result(
            chosen_method='ocr',
            markitdown_available=False,
            ocr_available=True,
            processing_time=3.0
        )
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 1
        assert self.stats.failed_processed == 0
        assert self.stats.markitdown_chosen == 0
        assert self.stats.ocr_chosen == 1
        assert self.stats.markitdown_only == 0
        assert self.stats.ocr_only == 1
        assert self.stats.both_failed == 0
        assert self.stats.total_processing_time == 3.0
        
    def test_add_dual_result_both_failed(self):
        """Test adding dual result when both methods failed."""
        self.stats.add_dual_result(
            chosen_method='none',
            markitdown_available=False,
            ocr_available=False,
            processing_time=1.0
        )
        
        assert self.stats.total_processed == 1
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 1
        assert self.stats.markitdown_chosen == 0
        assert self.stats.ocr_chosen == 0
        assert self.stats.markitdown_only == 0
        assert self.stats.ocr_only == 0
        assert self.stats.both_failed == 1
        assert self.stats.total_processing_time == 1.0
        
    def test_get_summary_empty(self):
        """Test getting summary when no processing occurred."""
        summary = self.stats.get_summary()
        
        assert summary['total_processed'] == 0
        assert summary['success_rate'] == 0.0
        assert summary['average_time_per_file'] == 0.0
        assert len(summary['method_stats']) == 0
        # No dual processing stats should be present for empty stats
        assert 'markitdown_chosen_pct' not in summary
        assert 'ocr_chosen_pct' not in summary
        
    def test_get_summary_with_data(self):
        """Test getting summary with processing data."""
        # Add some results
        self.stats.add_dual_result('markitdown', True, True, 1.0)
        self.stats.add_dual_result('ocr', True, True, 2.0)
        self.stats.add_dual_result('markitdown', True, True, 1.5)
        self.stats.add_dual_result('none', False, False, 0.5)
        
        summary = self.stats.get_summary()
        
        assert summary['total_processed'] == 4
        assert summary['successful_processed'] == 3  # 3 successful, 1 failed
        assert summary['failed_processed'] == 1
        assert summary['success_rate'] == 75.0  # 3/4 * 100
        assert summary['average_time_per_file'] == 1.25  # 5.0/4
        assert summary['markitdown_chosen'] == 2
        assert summary['ocr_chosen'] == 1
        assert summary['both_failed'] == 1
        assert summary['markitdown_chosen_pct'] == 50.0  # 2/4 * 100
        assert summary['ocr_chosen_pct'] == 25.0  # 1/4 * 100
        
    def test_multiple_add_result_calls(self):
        """Test multiple sequential add_result calls."""
        self.stats.add_result('markitdown', True, 1.0)
        self.stats.add_result('ocr', True, 2.0)
        self.stats.add_result('markitdown', False, 0.5)
        
        assert self.stats.total_processed == 3
        assert self.stats.successful_processed == 2
        assert self.stats.failed_processed == 1
        assert self.stats.markitdown_chosen == 2  # Counts both successful and failed attempts
        assert self.stats.ocr_chosen == 1
        assert self.stats.total_processing_time == 3.5
        
    def test_mixed_result_types(self):
        """Test mixing add_result and add_dual_result calls."""
        self.stats.add_result('markitdown', True, 1.0)
        self.stats.add_dual_result('ocr', True, True, 2.0)
        
        assert self.stats.total_processed == 2
        assert self.stats.successful_processed == 2
        assert self.stats.markitdown_chosen == 1
        assert self.stats.ocr_chosen == 1
        assert self.stats.total_processing_time == 3.0
        
    def test_get_legacy_dict(self):
        """Test legacy dictionary format."""
        self.stats.add_dual_result('markitdown', True, True, 1.0)
        self.stats.add_dual_result('ocr', True, True, 2.0)
        
        legacy = self.stats.get_legacy_dict()
        
        assert legacy['total_processed'] == 2
        assert legacy['markitdown_chosen'] == 1
        assert legacy['ocr_chosen'] == 1
        assert legacy['markitdown_chosen_pct'] == 50.0
        assert legacy['ocr_chosen_pct'] == 50.0
        assert legacy['success_rate'] == 100.0
        
    def test_reset(self):
        """Test resetting statistics."""
        # Add some data
        self.stats.add_result('markitdown', True, 1.0)
        self.stats.add_dual_result('ocr', True, True, 2.0)
        
        # Verify data exists
        assert self.stats.total_processed == 2
        
        # Reset
        self.stats.reset()
        
        # Verify everything is reset
        assert self.stats.total_processed == 0
        assert self.stats.successful_processed == 0
        assert self.stats.failed_processed == 0
        assert self.stats.markitdown_chosen == 0
        assert self.stats.ocr_chosen == 0
        assert self.stats.total_processing_time == 0.0
        assert len(self.stats.method_stats) == 0