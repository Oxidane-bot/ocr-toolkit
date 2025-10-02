"""
Unit tests for OCR processor module.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.processors.ocr_processor import OCRProcessor
from ocr_toolkit.processors.base import ProcessingResult


class TestOCRProcessor:
    """Test cases for OCRProcessor class."""
    
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
        self.processor = OCRProcessor(self.mock_ocr_model)
        
        # Temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir, ignore_errors=True)
            
    def test_init(self):
        """Test OCRProcessor initialization."""
        assert self.processor is not None
        assert self.processor.ocr_model == self.mock_ocr_model
        assert self.processor.batch_size == 16  # default value
        
    def test_init_with_custom_batch_size(self):
        """Test OCRProcessor initialization with custom batch size."""
        processor = OCRProcessor(self.mock_ocr_model, batch_size=32)
        assert processor.batch_size == 32
        
    def test_supports_format_pdf(self):
        """Test format support for PDF files."""
        assert self.processor.supports_format(".pdf") == True
        assert self.processor.supports_format(".PDF") == True
        
    def test_supports_format_images(self):
        """Test format support for image files."""
        assert self.processor.supports_format(".jpg") == True
        assert self.processor.supports_format(".png") == True
        assert self.processor.supports_format(".jpeg") == True
        assert self.processor.supports_format(".tiff") == True
        
    def test_supports_format_office_docs(self):
        """Test format support for Office documents."""
        assert self.processor.supports_format(".docx") == True
        assert self.processor.supports_format(".pptx") == True
        assert self.processor.supports_format(".xlsx") == True

    def test_supports_format_text_files(self):
        """Test format support for text files."""
        assert self.processor.supports_format(".txt") == True
        assert self.processor.supports_format(".md") == True
        assert self.processor.supports_format(".rtf") == True

    def test_supports_format_unsupported(self):
        """Test format support for unsupported files."""
        assert self.processor.supports_format(".xyz") == False
        assert self.processor.supports_format(".unknown") == False
        
    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = self.processor.get_supported_formats()
        assert isinstance(formats, list)
        assert '.pdf' in formats
        assert '.jpg' in formats
        assert '.docx' in formats
        
    @patch('ocr_toolkit.processors.ocr_processor.OCRProcessor.process')
    def test_process_success_mock(self, mock_process):
        """Test main process method success with mock."""
        mock_result = ProcessingResult(
            success=True,
            content='OCR content',
            processing_time=1.5,
            method='OCR',
            file_path='test.pdf'
        )
        mock_process.return_value = mock_result
        
        result = self.processor.process('test.pdf', output_dir=self.output_dir)
        
        assert isinstance(result, ProcessingResult)
        assert result.success == True
        assert result.content == 'OCR content'
        assert result.processing_time == 1.5
        
    def test_process_unsupported_format(self):
        """Test processing unsupported format."""
        result = self.processor.process('test.txt', output_dir=self.output_dir)
        
        assert isinstance(result, ProcessingResult)
        assert result.success == False
        assert 'invalid file' in result.error.lower()
        
    def test_init_with_cnocr_enabled(self):
        """Test OCRProcessor initialization with CnOCR enabled."""
        with patch('ocr_toolkit.processors.ocr_processor.OCRProcessor._initialize_cnocr') as mock_init:
            processor = OCRProcessor(self.mock_ocr_model, use_cnocr=True)
            assert processor.use_cnocr == True
            mock_init.assert_called_once()
    
    def test_init_with_cnocr_disabled(self):
        """Test OCRProcessor initialization with CnOCR disabled."""
        processor = OCRProcessor(self.mock_ocr_model, use_cnocr=False)
        assert processor.use_cnocr == False
        assert not hasattr(processor, 'cnocr')
    
    def test_initialize_cnocr_success(self):
        """Test successful CnOCR initialization."""
        with patch('shutil.which', return_value='/path/to/huggingface-cli'), \
             patch('sys.executable', '/path/to/python.exe'), \
             patch('cnocr.CnOcr') as mock_cnocr:
            
            mock_cnocr_instance = Mock()
            mock_cnocr.return_value = mock_cnocr_instance
            
            processor = OCRProcessor(self.mock_ocr_model, use_cnocr=True)
            
            assert processor.use_cnocr == True
            assert hasattr(processor, 'cnocr')
            mock_cnocr.assert_called_once()
    
    def test_initialize_cnocr_import_error(self):
        """Test CnOCR initialization with import error."""
        with patch('builtins.__import__', side_effect=ImportError("CnOCR not available")):
            processor = OCRProcessor(self.mock_ocr_model, use_cnocr=True)
            assert processor.use_cnocr == False
            assert not hasattr(processor, 'cnocr')
    
    def test_initialize_cnocr_file_not_found_error(self):
        """Test CnOCR initialization with file not found error."""
        with patch('cnocr.CnOcr', side_effect=FileNotFoundError("Model file missing")):
            processor = OCRProcessor(self.mock_ocr_model, use_cnocr=True)
            assert processor.use_cnocr == False
            assert not hasattr(processor, 'cnocr')
    
    def test_initialize_cnocr_model_download_error(self):
        """Test CnOCR initialization with model download error."""
        with patch('cnocr.CnOcr', side_effect=Exception("model.onnx does not exists")):
            processor = OCRProcessor(self.mock_ocr_model, use_cnocr=True)
            assert processor.use_cnocr == False
            assert not hasattr(processor, 'cnocr')