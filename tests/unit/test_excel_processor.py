"""
Unit tests for Excel data processor module.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ocr_toolkit.processors.excel_processor import ExcelDataProcessor
from ocr_toolkit.processors.base import ProcessingResult


class TestExcelDataProcessor:
    """Test cases for ExcelDataProcessor class."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.processor = ExcelDataProcessor()

    def test_init(self):
        """Test ExcelDataProcessor initialization."""
        assert self.processor is not None
        assert hasattr(self.processor, 'logger')

    def test_supports_format_xlsx(self):
        """Test format support for .xlsx files."""
        assert self.processor.supports_format(".xlsx") is True
        assert self.processor.supports_format(".XLSX") is True
        assert self.processor.supports_format("xlsx") is True

    def test_supports_format_xls(self):
        """Test format support for .xls files."""
        assert self.processor.supports_format(".xls") is True
        assert self.processor.supports_format(".XLS") is True
        assert self.processor.supports_format("xls") is True

    def test_supports_format_unsupported(self):
        """Test format support for unsupported files."""
        assert self.processor.supports_format(".pdf") is False
        assert self.processor.supports_format(".docx") is False
        assert self.processor.supports_format(".txt") is False
        assert self.processor.supports_format(".csv") is False

    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = self.processor.get_supported_formats()
        assert isinstance(formats, list)
        assert '.xls' in formats
        assert '.xlsx' in formats
        assert len(formats) == 2

    def test_process_invalid_file(self):
        """Test processing non-existent file."""
        result = self.processor.process('nonexistent.xlsx')
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert 'invalid file' in result.error.lower()

    def test_process_unsupported_format(self):
        """Test processing unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test')
            temp_path = f.name

        try:
            result = self.processor.process(temp_path)
            assert isinstance(result, ProcessingResult)
            assert result.success is False
            assert 'unsupported file format' in result.error.lower()
        finally:
            os.unlink(temp_path)

    @patch('openpyxl.load_workbook')
    def test_process_password_protected(self, mock_load):
        """Test processing password-protected Excel file."""
        mock_load.side_effect = Exception('password protected workbook')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            result = self.processor.process(temp_path)
            assert isinstance(result, ProcessingResult)
            assert result.success is False
            assert 'password' in result.error.lower()
        finally:
            os.unlink(temp_path)

    @patch('openpyxl.load_workbook')
    def test_process_corrupted_file(self, mock_load):
        """Test processing corrupted Excel file."""
        mock_load.side_effect = Exception('invalid file format')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            result = self.processor.process(temp_path)
            assert isinstance(result, ProcessingResult)
            assert result.success is False
            assert 'corrupt' in result.error.lower() or 'invalid' in result.error.lower()
        finally:
            os.unlink(temp_path)

    def test_format_cell_value_none(self):
        """Test formatting None cell values."""
        assert self.processor._format_cell_value(None) == ''

    def test_format_cell_value_integer(self):
        """Test formatting integer cell values."""
        assert self.processor._format_cell_value(42) == '42'
        assert self.processor._format_cell_value(0) == '0'
        assert self.processor._format_cell_value(-100) == '-100'

    def test_format_cell_value_float(self):
        """Test formatting float cell values."""
        assert self.processor._format_cell_value(3.14) == '3.14'
        assert self.processor._format_cell_value(100.0) == '100'
        assert self.processor._format_cell_value(0.5) == '0.50'

    def test_format_cell_value_string(self):
        """Test formatting string cell values."""
        assert self.processor._format_cell_value('Hello') == 'Hello'
        assert self.processor._format_cell_value('') == ''

    def test_format_cell_value_with_pipe(self):
        """Test formatting cell values with pipe character."""
        result = self.processor._format_cell_value('value | with | pipes')
        assert '\\|' in result
        assert '|' not in result or result.count('|') == result.count('\\|')

    def test_format_cell_value_long_string(self):
        """Test formatting very long cell values."""
        long_string = 'a' * 200
        result = self.processor._format_cell_value(long_string)
        assert len(result) <= 100
        assert result.endswith('...')

    def test_format_cell_value_datetime(self):
        """Test formatting datetime cell values."""
        from datetime import datetime
        dt = datetime(2024, 12, 5, 14, 30, 0)
        result = self.processor._format_cell_value(dt)
        assert '2024-12-05' in result
        assert '14:30:00' in result


class TestExcelDataProcessorIntegration:
    """Integration tests using real openpyxl."""

    def setup_method(self):
        """Setup test fixtures."""
        self.processor = ExcelDataProcessor()

    def test_process_real_excel_file(self):
        """Test processing a real Excel file if samples exist."""
        # Try to find sample Excel files
        sample_files = [
            'test_files/excel_samples/Trial Balance Solutions.xlsx',
            'test_files/excel_samples/Income Statement Solutions.xlsx'
        ]

        excel_file = None
        for sample in sample_files:
            if os.path.exists(sample):
                excel_file = sample
                break

        if not excel_file:
            pytest.skip("No sample Excel files found for integration testing")

        result = self.processor.process(excel_file)

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.content
        assert result.pages > 0
        assert result.processing_time > 0
        assert result.method == 'excel_data'
        assert result.error == ''

        # Check that content contains expected Markdown structure
        assert '# ' in result.content  # File name header
        assert '## Sheet:' in result.content  # Sheet headers
        assert '|' in result.content  # Table rows

    def test_process_real_file_sheet_count(self):
        """Test that sheet count is correctly reported."""
        sample_file = 'test_files/excel_samples/Trial Balance Solutions.xlsx'

        if not os.path.exists(sample_file):
            pytest.skip("Sample Excel file not found")

        result = self.processor.process(sample_file)

        assert result.success is True
        # Trial Balance Solutions.xlsx has 6 sheets
        assert result.pages == 6

    def test_process_real_file_content_structure(self):
        """Test that processed content has proper Markdown structure."""
        sample_file = 'test_files/excel_samples/Trial Balance Solutions.xlsx'

        if not os.path.exists(sample_file):
            pytest.skip("Sample Excel file not found")

        result = self.processor.process(sample_file)

        assert result.success is True

        content = result.content

        # Should have file name as main header
        assert content.startswith('# Trial Balance Solutions.xlsx')

        # Should have sheet headers
        assert '## Sheet: Mindfulness Services' in content
        assert '## Sheet: The Green Restaurant' in content

        # Should have table structure (header separator)
        assert '| --- |' in content or '|---|' in content

        # Should have data rows
        lines = content.split('\n')
        table_rows = [l for l in lines if l.startswith('|')]
        assert len(table_rows) > 10  # Should have many table rows
