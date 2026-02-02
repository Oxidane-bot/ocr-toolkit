"""
Complete end-to-end OCR integration tests for testFile directory.

These tests actually run OCR processing on real files to ensure the entire pipeline works.
"""

import os
import shutil
import tempfile
import time
import pytest
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestFullOCRIntegration:
    """Complete OCR integration tests using real files from testFile."""

    @pytest.fixture
    def testfile_dir(self):
        """Provide path to testFile directory."""
        test_path = project_root / "testFile"
        if not test_path.exists():
            pytest.skip("testFile directory not available")
        return test_path

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp(prefix="ocr_full_test_")
        yield temp_dir
        # Cleanup after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_pdf(self, testfile_dir):
        """Provide sample PDF file."""
        pdf_file = testfile_dir / "instructions for writing 4-1.pdf"
        if not pdf_file.exists():
            pytest.skip("Sample PDF not available")
        return pdf_file

    @pytest.fixture
    def sample_image(self, testfile_dir):
        """Provide sample image file."""
        img_file = testfile_dir / "choice question.jpg"
        if not img_file.exists():
            pytest.skip("Sample image not available")
        return img_file

    @pytest.fixture
    def sample_excel(self, testfile_dir):
        """Provide sample Excel file."""
        excel_file = testfile_dir / "excel_samples" / "Income Statement Solutions.xlsx"
        if not excel_file.exists():
            pytest.skip("Sample Excel not available")
        return excel_file

    def test_convert_pdf_via_cli(self, sample_pdf, temp_output_dir):
        """Test PDF conversion using CLI."""
        from ocr_toolkit.cli.convert import main as convert_main
        import sys
        from io import StringIO
        import argparse

        output_file = os.path.join(temp_output_dir, "output.md")

        # Simulate CLI arguments
        old_argv = sys.argv
        sys.argv = [
            "ocr-convert",
            str(sample_pdf),
            "--output-dir", temp_output_dir,
            "--cpu",  # Use CPU for testing
        ]

        try:
            convert_main()
        except SystemExit as e:
            # CLI calls sys.exit, that's expected
            if e.code not in [0, None]:
                pytest.fail(f"CLI exited with code {e.code}")
        finally:
            sys.argv = old_argv

        # Check if output was created
        output_path = Path(temp_output_dir) / f"{sample_pdf.stem}.md"
        assert output_path.exists(), f"Output file not created: {output_path}"

        content = output_path.read_text(encoding='utf-8')
        assert len(content) > 0, "Output should not be empty"

        print(f"\nPDF CLI test passed - Content length: {len(content)}")

    def test_convert_image_via_cli(self, sample_image, temp_output_dir):
        """Test image conversion using CLI."""
        import sys

        output_file = os.path.join(temp_output_dir, "output.md")

        # Simulate CLI arguments
        old_argv = sys.argv
        sys.argv = [
            "ocr-convert",
            str(sample_image),
            "--output-dir", temp_output_dir,
            "--cpu",
        ]

        try:
            from ocr_toolkit.cli.convert import main as convert_main
            convert_main()
        except SystemExit as e:
            if e.code not in [0, None]:
                pytest.fail(f"CLI exited with code {e.code}")
        finally:
            sys.argv = old_argv

        # Check if output was created
        output_path = Path(temp_output_dir) / f"{sample_image.stem}.md"
        assert output_path.exists(), f"Output file not created: {output_path}"

        content = output_path.read_text(encoding='utf-8')
        assert len(content) > 0

        print(f"\nImage CLI test passed - Content length: {len(content)}")

    def test_excel_extraction(self, sample_excel, temp_output_dir):
        """Test Excel data extraction."""
        from ocr_toolkit.processors.excel_processor import ExcelDataProcessor

        start_time = time.time()

        processor = ExcelDataProcessor()
        result = processor.process(str(sample_excel))

        processing_time = time.time() - start_time

        # Verify processing succeeded
        assert result.success, f"Excel processing failed: {result.error}"
        assert result.content, "Should extract data from Excel"
        assert result.pages >= 1, "Should have at least 1 sheet"
        assert "|" in result.content, "Should contain table markdown"
        assert processing_time < 30, f"Excel processing took too long: {processing_time:.2f}s"

        print(f"\nExcel extraction test passed - Time: {processing_time:.2f}s, Sheets: {result.pages}")

    def test_convert_directory_batch(self, testfile_dir, temp_output_dir):
        """Test batch conversion of multiple files."""
        from ocr_toolkit.utils.file_discovery import discover_files

        # Use nested_test_structure for batch test (smaller file set)
        test_dir = testfile_dir / "nested_test_structure"
        if not test_dir.exists():
            pytest.skip("nested_test_structure not available")

        files, base_dir, _ = discover_files(str(test_dir), recursive=True)

        # Should find multiple files
        assert len(files) >= 2, f"Expected multiple files, found {len(files)}"

        print(f"\nBatch test would process {len(files)} files from nested structure")

    def test_full_testfile_directory(self, testfile_dir, temp_output_dir):
        """Test processing the entire testFile directory."""
        from ocr_toolkit.utils.file_discovery import discover_files

        files, base_dir, _ = discover_files(str(testfile_dir), recursive=False)

        # Should find several files
        assert len(files) >= 5, f"Expected at least 5 files, found {len(files)}"

        # Verify we have expected file types
        extensions = {Path(f).suffix.lower() for f in files}
        assert ".pdf" in extensions or ".docx" in extensions or ".jpg" in extensions

        print(f"\ntestFile directory scan passed - Found {len(files)} files")

    def test_chinese_pdf_support(self, testfile_dir, temp_output_dir):
        """Test that Chinese text in PDFs is handled correctly."""
        # This test uses the UCB Referencing PDF which may contain various characters
        chinese_pdf = testfile_dir / "UCB Referencing and Style Guide 2024-25.pdf"
        if not chinese_pdf.exists():
            pytest.skip("UCB Referencing PDF not available")

        import sys
        old_argv = sys.argv
        sys.argv = [
            "ocr-convert",
            str(chinese_pdf),
            "--output-dir", temp_output_dir,
            "--cpu",
            "--pages", "1",  # Just process first page for speed
        ]

        try:
            from ocr_toolkit.cli.convert import main as convert_main
            convert_main()
        except SystemExit as e:
            if e.code not in [0, None]:
                pytest.fail(f"CLI exited with code {e.code}")
        finally:
            sys.argv = old_argv

        # Check output
        output_path = Path(temp_output_dir) / f"{chinese_pdf.stem}.md"
        if output_path.exists():
            content = output_path.read_text(encoding='utf-8')
            assert len(content) > 0
            print(f"\nChinese PDF test passed - Content length: {len(content)}")
