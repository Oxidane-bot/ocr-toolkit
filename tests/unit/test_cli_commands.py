"""
Unit tests for CLI commands.
"""

import pytest
import os
import sys
import subprocess
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.cli import convert, extract


class TestCLICommands:
    """Test cases for CLI commands."""
    
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_convert_create_parser(self):
        """Test convert command parser creation."""
        parser = convert.create_parser()
        assert parser is not None
        assert parser.prog == 'ocr-convert'
        
    def test_convert_validate_arguments_list_formats(self):
        """Test convert argument validation for list-formats."""
        from argparse import Namespace
        args = Namespace(list_formats=True, workers=4)
        assert convert.validate_arguments(args) is True
        
    def test_convert_validate_arguments_no_input(self):
        """Test convert argument validation without input path."""
        from argparse import Namespace
        args = Namespace(list_formats=False, input_path=None, workers=4)
        assert convert.validate_arguments(args) is False
        
    def test_convert_validate_arguments_invalid_workers(self):
        """Test convert argument validation with invalid workers."""
        from argparse import Namespace
        args = Namespace(list_formats=False, input_path='/test', workers=0)
        assert convert.validate_arguments(args) is False
        
    def test_convert_list_supported_formats(self):
        """Test list supported formats function."""
        # This function now has safe fallback logic, just test it doesn't crash
        try:
            convert.list_supported_formats()
        except Exception as e:
            pytest.fail(f"list_supported_formats() should not raise an exception: {e}")
            
    def test_extract_create_parser(self):
        """Test extract command parser creation."""
        parser = extract.create_parser()
        assert parser is not None
        assert parser.prog == 'ocr-extract'
        
    @patch('ocr_toolkit.cli.extract.load_ocr_model')
    @patch('ocr_toolkit.cli.extract.discover_files')
    @patch('ocr_toolkit.cli.extract.dual_processor.create_dual_processor')
    def test_extract_main_no_files(self, mock_create_processor, mock_discover, mock_load_model):
        """Test extract main function when no files found."""
        mock_discover.return_value = ([], '/test')
        mock_load_model.return_value = Mock()
        mock_create_processor.return_value = Mock()
        
        with patch('sys.argv', ['ocr-extract', '/test/path']):
            with pytest.raises(SystemExit) as exc_info:
                extract.main()
            assert exc_info.value.code == 1
                
        
    @patch('sys.argv', ['ocr-extract', '--help'])
    def test_extract_help_functionality(self):
        """Test that extract command can show help without errors."""
        from argparse import ArgumentParser
        
        # Create parser and test help doesn't raise exceptions
        parser = extract.create_parser()
        try:
            parser.parse_args(['--help'])
        except SystemExit as e:
            # argparse exits with code 0 for help
            assert e.code == 0
            
    @patch('sys.argv', ['convert', '--help'])            
    def test_convert_help_functionality(self):
        """Test that convert command can show help without errors."""
        from argparse import ArgumentParser
        
        # Create parser and test help doesn't raise exceptions
        parser = convert.create_parser()
        try:
            parser.parse_args(['--help'])
        except SystemExit as e:
            # argparse exits with code 0 for help
            assert e.code == 0