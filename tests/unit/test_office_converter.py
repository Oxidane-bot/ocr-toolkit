"""
Unit tests for OfficeConverter Linux compatibility behavior.
"""

import os
import sys
from unittest.mock import Mock, patch

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit.converters import office_converter
from ocr_toolkit.converters.strategies.libreoffice import LibreOfficeStrategy


def test_init_linux_uses_libreoffice_strategy(monkeypatch):
    """Linux should use LibreOffice strategy as the primary Office converter."""
    # Mock platform.system to return 'linux'
    monkeypatch.setattr(office_converter.platform, "system", lambda: "linux")

    converter = office_converter.OfficeConverter()

    # Should have LibreOffice strategy if available, plus docx2pdf as fallback
    assert len(converter.strategies) >= 1
    assert any(isinstance(s, LibreOfficeStrategy) for s in converter.strategies)


def test_convert_docx_on_linux_does_not_use_docx_fallback(monkeypatch):
    """Linux .docx should route through strategy matching, not docx2pdf fallback path."""
    # Mock platform.system to return 'linux'
    monkeypatch.setattr(office_converter.platform, "system", lambda: "linux")
    converter = office_converter.OfficeConverter()

    strategy = Mock()
    strategy.supports_format.return_value = True
    strategy.convert.return_value = {
        "method": "libreoffice",
        "success": True,
        "processing_time": 0.01,
        "error": "",
    }
    converter.strategies = [strategy]
    converter._convert_docx_with_fallback = Mock(side_effect=AssertionError("should not be called"))

    result = converter.convert_to_pdf("sample.docx", "out.pdf")

    converter._convert_docx_with_fallback.assert_not_called()
    strategy.supports_format.assert_called_once_with(".docx")
    strategy.convert.assert_called_once_with("sample.docx", "out.pdf")
    assert result["success"] is True
    assert result["method"] == "libreoffice"


def test_convert_docx_on_windows_uses_fallback(monkeypatch):
    """Non-Linux .docx should still use docx2pdf -> Word COM fallback path."""
    # Mock platform.system to return 'windows'
    monkeypatch.setattr(office_converter.platform, "system", lambda: "windows")
    converter = office_converter.OfficeConverter()

    fake_result = {
        "method": "docx2pdf",
        "success": True,
        "processing_time": 0.01,
        "error": "",
    }
    with patch.object(converter, "_convert_docx_with_fallback", return_value=fake_result) as mocked:
        result = converter.convert_to_pdf("sample.docx", "out.pdf")

    mocked.assert_called_once_with("sample.docx", "out.pdf")
    assert result == fake_result


def test_linux_supported_formats_include_office_extensions(monkeypatch):
    """Linux supported formats should come from LibreOffice strategy coverage."""
    # Mock platform.system to return 'linux'
    monkeypatch.setattr(office_converter.platform, "system", lambda: "linux")
    converter = office_converter.OfficeConverter()

    # Check that LibreOffice formats are included
    supported = converter.get_supported_formats()
    expected_formats = [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"]
    for fmt in expected_formats:
        assert fmt in supported


def test_libreoffice_strategy_reports_missing_soffice(monkeypatch):
    """Conversion should fail with a clear message when soffice is unavailable."""
    monkeypatch.setattr("ocr_toolkit.converters.strategies.libreoffice.shutil.which", lambda _name: None)

    strategy = LibreOfficeStrategy()
    result = strategy.convert("input.docx", "output.pdf")

    assert result["success"] is False
    assert result["method"] == "libreoffice"
    assert "LibreOffice not found" in result["error"]
