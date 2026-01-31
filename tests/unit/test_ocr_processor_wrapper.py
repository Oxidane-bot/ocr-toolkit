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
        # Temporary directories
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup after each test method."""
        import pathlib
        test_dir_path = pathlib.Path(self.test_dir)
        if test_dir_path.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_default_engine(self):
        """Test OCRProcessorWrapper initialization with default engine."""
        # Mock the PaddleOCRVLHandler to avoid actual model loading
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler.return_value = mock_instance

            processor = OCRProcessorWrapper()

            assert processor is not None
            assert processor.engine == "paddleocr_vl"
            assert processor.batch_size == 16
            assert processor.use_gpu is True

    def test_init_paddleocr_engine(self):
        """Test OCRProcessorWrapper initialization with paddleocr engine."""
        with patch('ocr_toolkit.processors.paddleocr_handler.PaddleOCRHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler.return_value = mock_instance

            processor = OCRProcessorWrapper(engine="paddleocr")

            assert processor.engine == "paddleocr"

    def test_init_doc_understanding_engine(self):
        """Test OCRProcessorWrapper initialization with doc_understanding engine."""
        with patch('ocr_toolkit.processors.doc_understanding_handler.DocUnderstandingHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler.return_value = mock_instance

            processor = OCRProcessorWrapper(engine="doc_understanding")

            assert processor.engine == "doc_understanding"

    def test_init_with_cpu(self):
        """Test OCRProcessorWrapper initialization with CPU mode."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler.return_value = mock_instance

            processor = OCRProcessorWrapper(use_gpu=False)

            assert processor.use_gpu is False

    def test_init_with_custom_batch_size(self):
        """Test OCRProcessorWrapper initialization with custom batch size."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler.return_value = mock_instance

            processor = OCRProcessorWrapper(batch_size=32)

            assert processor.batch_size == 32

    def test_process_document_success(self):
        """Test successful document processing."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            # Setup mock handler
            mock_handler = Mock()
            mock_handler.is_available.return_value = True
            mock_handler.process_document.return_value = ("Test markdown content", {'page_count': 1})
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            # Mock args
            args = Namespace()

            result = processor.process_document("test.png", args)

            assert result['success'] is True
            assert result['chosen_method'] == 'paddleocr_vl'
            assert result['final_content'] == "Test markdown content"
            assert result['pages'] == 1
            assert 'ocr_result' in result

    def test_process_document_with_pages(self):
        """Test document processing with page selection."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.is_available.return_value = True
            mock_handler.process_document.return_value = ("Test content", {'page_count': 2, 'selected_pages': [0, 1]})
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            args = Namespace(pages="1-2")

            result = processor.process_document("test.pdf", args)

            assert result['success'] is True
            assert result['pages'] == 2

    def test_process_document_with_profile(self):
        """Test document processing with profiling enabled."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.is_available.return_value = True
            mock_handler.process_document.return_value = ("Test content", {'page_count': 1})
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            args = Namespace(profile=True)

            result = processor.process_document("test.png", args)

            assert result['success'] is True

    def test_process_document_handler_not_available(self):
        """Test document processing when handler is not available."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.is_available.return_value = False
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            args = Namespace()

            result = processor.process_document("test.png", args)

            assert result['success'] is False
            assert 'handler not available' in result['error'].lower()

    def test_get_statistics(self):
        """Test statistics calculation."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.is_available.return_value = True
            mock_handler.process_document.return_value = ("Test", {'page_count': 1})
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            stats = processor.get_statistics()

            assert 'ocr_processed' in stats
            assert 'success_rate' in stats
            assert stats['ocr_processed'] == 1
            assert stats['success_rate'] == 100.0

    def test_get_detailed_statistics(self):
        """Test detailed statistics calculation."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.is_available.return_value = True
            mock_handler.process_document.return_value = ("Test", {'page_count': 1})
            mock_handler_class.return_value = mock_handler

            processor = OCRProcessorWrapper()

            stats = processor.get_detailed_statistics()

            assert 'ocr_processed' in stats
            assert 'success_rate' in stats

    def test_create_ocr_processor_wrapper_default(self):
        """Test factory function with default parameters."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper()

            assert isinstance(processor, OCRProcessorWrapper)
            assert processor.engine == "paddleocr_vl"

    def test_create_ocr_processor_wrapper_with_engine(self):
        """Test factory function with custom engine."""
        with patch('ocr_toolkit.processors.paddleocr_handler.PaddleOCRHandler') as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper(engine="paddleocr")

            assert isinstance(processor, OCRProcessorWrapper)
            assert processor.engine == "paddleocr"

    def test_create_ocr_processor_wrapper_with_cpu(self):
        """Test factory function with CPU mode."""
        with patch('ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler') as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper(use_gpu=False)

            assert isinstance(processor, OCRProcessorWrapper)
            assert processor.use_gpu is False
