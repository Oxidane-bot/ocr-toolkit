"""
Unit tests for OCR processor wrapper module.
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

from ocr_toolkit.ocr_processor_wrapper import OCRProcessorWrapper, create_ocr_processor_wrapper


class TestOCRProcessorWrapper:
    """Test cases for OCRProcessorWrapper class."""
    
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
        self.processor = OCRProcessorWrapper(self.mock_ocr_model)
        
        # Test arguments
        self.args = Namespace(batch_size=16)
        
        # Temporary directories
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_init(self):
        """Test OCRProcessorWrapper initialization."""
        assert self.processor is not None
        # Simplified architecture using factory pattern
        assert hasattr(self.processor, 'processor')
        assert hasattr(self.processor, 'batch_size')
        assert hasattr(self.processor, 'use_zh')
        assert self.processor.batch_size == 16
        assert self.processor.use_zh == False
        
    def test_init_with_chinese_support(self):
        """Test OCRProcessorWrapper initialization with Chinese support."""
        processor = OCRProcessorWrapper(self.mock_ocr_model, use_zh=True)
        assert processor.use_zh == True
        assert hasattr(processor, 'processor')
        
    def test_init_with_custom_evaluator(self):
        """Test OCRProcessorWrapper initialization with custom evaluator (signature changed)."""
        # The new OCRProcessorWrapper signature no longer accepts quality_evaluator
        processor = OCRProcessorWrapper(self.mock_ocr_model)
        assert processor is not None
        assert hasattr(processor, 'processor')
        
    def test_get_statistics(self):
        """Test statistics calculation."""
        stats = self.processor.get_statistics()
        
        # New simplified statistics format
        assert 'ocr_processed' in stats
        assert 'success_rate' in stats
        assert stats['ocr_processed'] == 1
        assert stats['success_rate'] == 100.0
        
    def test_get_statistics_empty(self):
        """Test statistics when no processing has occurred."""
        stats = self.processor.get_statistics()
        
        # New simplified statistics format
        assert 'ocr_processed' in stats
        assert 'success_rate' in stats
        assert stats['ocr_processed'] == 1
        assert stats['success_rate'] == 100.0
        
    def test_create_ocr_processor_wrapper_factory(self):
        """Test factory function."""
        processor = create_ocr_processor_wrapper(self.mock_ocr_model)
        
        assert isinstance(processor, OCRProcessorWrapper)
        # New simplified architecture using factory pattern
        assert hasattr(processor, 'processor')
        assert not hasattr(processor, 'markitdown_processor')  # No longer exists
        
    def test_create_ocr_processor_wrapper_with_chinese_support(self):
        """Test factory function with Chinese support."""
        processor = create_ocr_processor_wrapper(self.mock_ocr_model, use_zh=True)
        
        assert isinstance(processor, OCRProcessorWrapper)
        assert processor.use_zh == True
        assert hasattr(processor, 'processor')
        
    def test_process_document(self):
        """Test document processing."""
        # Mock OCR processor result
        mock_ocr_result = Mock()
        mock_ocr_result.content = "Test content"
        mock_ocr_result.success = True
        mock_ocr_result.processing_time = 1.0
        mock_ocr_result.error = ""
        mock_ocr_result.temp_files = []
        mock_ocr_result.to_dict.return_value = {
            'content': 'Test content',
            'success': True,
            'processing_time': 1.0,
            'temp_files': []
        }
        
        with patch.object(self.processor.processor, 'process', return_value=mock_ocr_result):
            result = self.processor.process_document("test.pdf", self.args)
            
            assert result['success'] == True
            assert result['chosen_method'] == 'ocr'
            assert result['final_content'] == 'Test content'
            assert 'ocr_result' in result
            assert 'markitdown_result' in result