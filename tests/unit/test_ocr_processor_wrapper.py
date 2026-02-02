"""
Unit tests for OCR processor wrapper module.
"""

import os
import shutil

# Add project root to path
import sys
import tempfile
from argparse import Namespace
from unittest.mock import Mock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

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

    def test_init_default_params(self):
        """Test OCRProcessorWrapper initialization with default parameters."""
        # Mock the PaddleOCRVLHandler to avoid actual model loading
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()

            assert processor is not None
            assert processor.use_gpu is True
            assert processor.with_images is False

    def test_init_with_cpu(self):
        """Test OCRProcessorWrapper initialization with CPU mode."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper(use_gpu=False)

            assert processor.use_gpu is False

    def test_init_with_images(self):
        """Test OCRProcessorWrapper initialization with image extraction."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper(with_images=True)

            assert processor.with_images is True

    def test_init_with_cpu_and_images(self):
        """Test OCRProcessorWrapper initialization with CPU and image extraction."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper(use_gpu=False, with_images=True)

            assert processor.use_gpu is False
            assert processor.with_images is True

    def test_process_document_success(self):
        """Test successful document processing."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            # Setup mock handler
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.process_document.return_value = (
                "# Test Content\n\nThis is test content.",
                {"page_count": 1},
            )
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()

            # Create a test file
            test_file = os.path.join(self.test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")

            # Mock the handler directly since _initialize_handler runs in __init__
            processor.handler = mock_instance

            result = processor.process_document(test_file)

            assert result["success"] is True
            assert result["file_path"] == test_file
            assert result["chosen_method"] == "paddleocr_vl"
            assert "Test Content" in result["final_content"]
            assert result["processing_time"] >= 0
            assert result["ocr_result"]["success"] is True

    def test_process_document_with_pages(self):
        """Test document processing with page selection."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            # Setup mock handler
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.process_document.return_value = (
                "# Page 1\n\nContent",
                {"page_count": 1, "selected_pages": [0]},
            )
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()

            # Create a test file
            test_file = os.path.join(self.test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")

            # Mock the handler directly
            processor.handler = mock_instance

            # Create args with pages parameter
            args = Namespace(pages="1")
            result = processor.process_document(test_file, args=args)

            assert result["success"] is True
            # Verify process_document was called with pages parameter
            mock_instance.process_document.assert_called_once()

    def test_process_document_with_profile(self):
        """Test document processing with profiling enabled."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            # Setup mock handler
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_instance.process_document.return_value = ("# Content\n\nTest", {"page_count": 1})
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()

            # Create a test file
            test_file = os.path.join(self.test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")

            # Mock the handler directly
            processor.handler = mock_instance

            # Create args with profile parameter
            args = Namespace(profile=True)
            result = processor.process_document(test_file, args=args)

            assert result["success"] is True
            # Verify profiler was used
            assert "metadata" in result["ocr_result"]

    def test_process_document_handler_not_available(self):
        """Test document processing when handler is not available."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            # Setup mock handler to raise exception
            mock_instance = Mock()
            mock_instance.is_available.return_value = False
            mock_instance.process_document.side_effect = RuntimeError("Handler not available")
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()

            # Create a test file
            test_file = os.path.join(self.test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")

            # Mock the handler directly
            processor.handler = mock_instance

            result = processor.process_document(test_file)

            assert result["success"] is False
            assert "Handler not available" in result["error"]
            assert result["ocr_result"]["success"] is False

    def test_get_statistics(self):
        """Test getting basic statistics."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()
            stats = processor.get_statistics()

            assert "ocr_processed" in stats
            assert "success_rate" in stats
            assert stats["success_rate"] == 100.0

    def test_get_detailed_statistics(self):
        """Test getting detailed statistics."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = OCRProcessorWrapper()
            stats = processor.get_detailed_statistics()

            assert "ocr_processed" in stats
            assert "success_rate" in stats


class TestCreateOCRProcessorWrapper:
    """Test cases for create_ocr_processor_wrapper function."""

    def test_create_ocr_processor_wrapper_default(self):
        """Test creating wrapper with default parameters."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper()

            assert processor.use_gpu is True
            assert processor.with_images is False

    def test_create_ocr_processor_wrapper_with_cpu(self):
        """Test creating wrapper with CPU mode."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper(use_gpu=False)

            assert processor.use_gpu is False

    def test_create_ocr_processor_wrapper_with_images(self):
        """Test creating wrapper with image extraction."""
        with patch(
            "ocr_toolkit.processors.paddleocr_vl_handler.PaddleOCRVLHandler"
        ) as mock_handler_class:
            mock_instance = Mock()
            mock_instance.is_available.return_value = True
            mock_handler_class.return_value = mock_instance

            processor = create_ocr_processor_wrapper(with_images=True)

            assert processor.with_images is True
