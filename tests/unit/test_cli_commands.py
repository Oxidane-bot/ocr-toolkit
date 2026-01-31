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

from ocr_toolkit.cli import convert


class TestCLICommands:
    """Test cases for CLI commands."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup after each test method."""
        # Use pathlib instead of os.path.exists to avoid PaddleOCR os module override
        import pathlib
        test_dir_path = pathlib.Path(self.test_dir)
        if test_dir_path.exists():
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

    # Tests for extract and search commands are removed as those modules don't exist
    # TODO: Add tests for new paddleocr_vl engine functionality
