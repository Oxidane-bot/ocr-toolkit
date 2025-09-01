"""
Unit tests for dual processor module.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

# Add project root to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.dual_processor import DualProcessor, create_dual_processor
from ocr_toolkit.quality_evaluator import QualityEvaluator


class TestDualProcessor:
    """Test cases for DualProcessor class."""
    
    def setup_method(self):
        """Setup test fixtures before each test method."""
        # Mock OCR model
        self.mock_ocr_model = Mock()
        mock_page = Mock()
        mock_page.render.return_value = "OCR extracted text"
        mock_result = Mock()
        mock_result.pages = [mock_page]
        self.mock_ocr_model.return_value = mock_result
        
        # Create processor
        self.processor = DualProcessor(self.mock_ocr_model)
        
        # Test arguments
        self.args = Namespace(batch_size=16)
        
        # Temporary directories
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_init(self):
        """Test DualProcessor initialization."""
        assert self.processor is not None
        assert isinstance(self.processor.quality_evaluator, QualityEvaluator)
        # New architecture uses ProcessingStats instead of dict
        assert hasattr(self.processor.stats, 'total_processed')
        assert self.processor.stats.total_processed == 0
        # Processors are now attributes
        assert hasattr(self.processor, 'ocr_processor')
        assert hasattr(self.processor, 'markitdown_processor')
        
    def test_init_with_custom_evaluator(self):
        """Test DualProcessor initialization with custom evaluator."""
        custom_evaluator = QualityEvaluator()
        processor = DualProcessor(self.mock_ocr_model, custom_evaluator)
        assert processor.quality_evaluator == custom_evaluator
        
                
    def test_get_statistics(self):
        """Test statistics calculation."""
        # Simulate some processing by directly adding to stats
        self.processor.stats.add_dual_result(
            chosen_method='markitdown',
            markitdown_available=True,
            ocr_available=True
        )
        self.processor.stats.add_dual_result(
            chosen_method='ocr',
            markitdown_available=False,
            ocr_available=True
        )
        
        stats = self.processor.get_statistics()
        
        assert stats['total_processed'] == 2
        assert stats['markitdown_chosen'] == 1
        assert stats['ocr_chosen'] == 1
        
    def test_get_statistics_empty(self):
        """Test statistics when no processing has occurred."""
        stats = self.processor.get_statistics()
        
        assert stats['total_processed'] == 0
        assert 'markitdown_chosen_pct' not in stats
        
    def test_create_dual_processor_factory(self):
        """Test factory function."""
        processor = create_dual_processor(self.mock_ocr_model)
        
        assert isinstance(processor, DualProcessor)
        # In new architecture, OCR model is wrapped in OCRProcessor
        assert hasattr(processor, 'ocr_processor')
        assert hasattr(processor, 'markitdown_processor')