"""
Unit tests for MarkItDown processor module.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.markitdown_processor import process_single_document


class TestMarkItDownProcessor:
    """Test cases for MarkItDown processor functions."""
    
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.test_output_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        
    def test_process_single_document_success(self):
        """Test successful document processing."""
        # Use a temporary directory instead of individual file to avoid Windows issues
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_input.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("Test content for processing")
            
            # Mock MarkItDown
            with patch('ocr_toolkit.markitdown_processor.MarkItDown') as mock_md:
                mock_result = Mock()
                mock_result.text_content = "# Test Document\n\nTest content for processing"
                mock_md.return_value.convert.return_value = mock_result
                
                # Test processing
                result = process_single_document(test_file, self.test_output_dir)
                
                # Verify result
                assert result['success'] is True
                assert result['file_path'] == test_file
                assert result['file_name'] == os.path.basename(test_file)
                assert result['processing_time'] >= 0  # Allow 0 for fast operations
                assert result['text_length'] > 0
                assert result['output_size'] > 0
                assert result['error'] == ''
                
                # Verify output file exists
                assert os.path.exists(result['output_file'])
                
                # Verify content
                with open(result['output_file'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert "Test Document" in content
                    assert "Test content" in content
    
    def test_process_nonexistent_file(self):
        """Test processing of non-existent file."""
        nonexistent_file = "nonexistent_file.txt"
        
        result = process_single_document(nonexistent_file, self.test_output_dir)
        
        assert result['success'] is False
        assert result['error'] != ''
        assert "No such file or directory" in result['error'] or "cannot find" in result['error'].lower()
        
    def test_process_document_with_markitdown_error(self):
        """Test handling when MarkItDown fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_error.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("Test content")
            
            # Mock MarkItDown to raise an exception
            with patch('ocr_toolkit.markitdown_processor.MarkItDown') as mock_md:
                mock_md.return_value.convert.side_effect = Exception("MarkItDown processing failed")
                
                result = process_single_document(test_file, self.test_output_dir)
                
                assert result['success'] is False
                assert result['error'] == "MarkItDown processing failed"
                assert result['processing_time'] >= 0
                
    def test_output_directory_creation(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_output.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("Test content")
            
            # Use non-existent output directory
            new_output_dir = os.path.join(self.test_output_dir, "new_subdir")
            
            with patch('ocr_toolkit.markitdown_processor.MarkItDown') as mock_md:
                mock_result = Mock()
                mock_result.text_content = "Test content"
                mock_md.return_value.convert.return_value = mock_result
                
                result = process_single_document(test_file, new_output_dir)
                
                assert result['success'] is True
                assert os.path.exists(new_output_dir)
                assert os.path.exists(result['output_file'])
                
    def test_result_structure(self):
        """Test that result dictionary has expected structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = os.path.join(temp_dir, "test_structure.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("Test content")
            
            with patch('ocr_toolkit.markitdown_processor.MarkItDown') as mock_md:
                mock_result = Mock()
                mock_result.text_content = "Test content"
                mock_md.return_value.convert.return_value = mock_result
                
                result = process_single_document(test_file, self.test_output_dir)
                
                # Check all expected keys exist
                expected_keys = {
                    'file_path', 'file_name', 'success', 'processing_time',
                    'output_file', 'output_size', 'text_length', 'error'
                }
                assert set(result.keys()) == expected_keys
                
                # Check data types
                assert isinstance(result['file_path'], str)
                assert isinstance(result['file_name'], str)
                assert isinstance(result['success'], bool)
                assert isinstance(result['processing_time'], (int, float))
                assert isinstance(result['output_file'], str)
                assert isinstance(result['output_size'], int)
                assert isinstance(result['text_length'], int)
                assert isinstance(result['error'], str)