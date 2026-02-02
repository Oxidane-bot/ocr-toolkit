"""
Complete end-to-end OCR integration tests for testFile directory.

These tests actually run OCR processing on real files to ensure the entire pipeline works.
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

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
    def sample_docx(self, testfile_dir):
        """Provide sample DOCX file."""
        docx_file = testfile_dir / "Mock Exam 2.docx"
        if not docx_file.exists():
            pytest.skip("Sample DOCX not available")
        return docx_file

    @pytest.fixture
    def sample_pptx(self, testfile_dir):
        """Provide sample PPTX file."""
        pptx_file = testfile_dir / "Week12 - summary.pptx"
        if not pptx_file.exists():
            pytest.skip("Sample PPTX not available")
        return pptx_file

    @pytest.fixture
    def sample_excel(self, testfile_dir):
        """Provide sample Excel file."""
        excel_file = testfile_dir / "excel_samples" / "Trial Balance Solutions.xlsx"
        if not excel_file.exists():
            pytest.skip("Sample Excel not available")
        return excel_file

    def test_ocr_extract_pdf(self, sample_pdf, temp_output_dir):
        """Test OCR extraction on real PDF file."""
        import argparse

        output_file = os.path.join(temp_output_dir, "output.md")

        # Mock sys.argv for CLI
        args = argparse.Namespace(
            input_path=str(sample_pdf),
            output=output_file,
            markitdown_only=False,
            ocr_only=True,  # Use OCR only for faster test
            fast=True,  # Fast mode
            pages=None,
            profile=False,
            show_selection=False,
            preserve_structure=False,
            recursive=False,
            cpu=False,
            det_arch="db_resnet50",
            reco_arch="crnn_vgg16_bn",
            batch_size=1,
            workers=1,
            timeout=60,
            zh=False,
            threads=None,
        )

        start_time = time.time()

        # Import and run processor directly
        from ocr_toolkit.processors.ocr_processor import OCRProcessor
        from ocr_toolkit.utils.model_loader import load_ocr_model

        model = load_ocr_model(args.det_arch, args.reco_arch, args.cpu)
        processor = OCRProcessor(model)

        result = processor.process(str(sample_pdf), fast=True, pages="1")

        processing_time = time.time() - start_time

        # Verify processing succeeded
        assert result.success, f"OCR processing failed: {result.error}"
        assert result.content, "OCR should extract some content"
        assert len(result.content) > 0, "Content should not be empty"
        assert processing_time < 120, f"Processing took too long: {processing_time:.2f}s"

        print(
            f"\nPDF OCR test passed - Time: {processing_time:.2f}s, Content length: {len(result.content)}"
        )

    def test_ocr_extract_image(self, sample_image, temp_output_dir):
        """Test OCR extraction on real image file."""
        from ocr_toolkit.processors.ocr_processor import OCRProcessor
        from ocr_toolkit.utils.model_loader import load_ocr_model

        start_time = time.time()

        model = load_ocr_model("db_resnet50", "crnn_vgg16_bn", use_cpu=False)
        processor = OCRProcessor(model)

        result = processor.process(str(sample_image))

        processing_time = time.time() - start_time

        # Verify processing succeeded
        assert result.success, f"Image OCR failed: {result.error}"
        assert result.content, "Should extract text from image"
        assert len(result.content) > 0
        assert processing_time < 60, f"Image processing took too long: {processing_time:.2f}s"

        print(
            f"\nImage OCR test passed - Time: {processing_time:.2f}s, Content length: {len(result.content)}"
        )

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
        assert result.pages == 6, "Should have 6 sheets"
        assert "|" in result.content, "Should contain table markdown"
        assert processing_time < 30, f"Excel processing took too long: {processing_time:.2f}s"

        print(
            f"\nExcel extraction test passed - Time: {processing_time:.2f}s, Sheets: {result.pages}"
        )

    def test_convert_directory_batch(self, testfile_dir, temp_output_dir):
        """Test batch conversion of multiple files."""
        from ocr_toolkit.utils.file_discovery import discover_files

        # Use nested_test_structure for batch test (smaller file set)
        test_dir = testfile_dir / "nested_test_structure"
        if not test_dir.exists():
            pytest.skip("nested_test_structure not available")

        files, base_dir, _ = discover_files(str(test_dir))

        # Should find multiple files
        assert len(files) >= 3, f"Expected multiple files, found {len(files)}"

        print(f"\nBatch test would process {len(files)} files from nested structure")
        # Note: We don't actually run full batch conversion in tests to keep it fast
        # Full batch tests should be in manual/benchmark tests

    def test_ocr_with_chinese_support(self, sample_pdf, temp_output_dir):
        """Test OCR with CnOCR (Chinese support) if available."""
        from ocr_toolkit.processors.ocr_processor import OCRProcessor

        try:
            # Initialize with Chinese support
            processor = OCRProcessor(ocr_model=None, use_cnocr=True)

            if not processor.cnocr_handler.is_available():
                pytest.skip("CnOCR not available, skipping Chinese OCR test")

            start_time = time.time()

            result = processor.process(str(sample_pdf), fast=True, pages="1")

            processing_time = time.time() - start_time

            assert result.success, f"CnOCR processing failed: {result.error}"
            assert result.content, "CnOCR should extract content"
            assert processing_time < 120, f"CnOCR took too long: {processing_time:.2f}s"

            print(f"\nCnOCR test passed - Time: {processing_time:.2f}s")

        except ImportError:
            pytest.skip("CnOCR dependencies not installed")

    @pytest.mark.slow
    def test_full_testfile_directory(self, testfile_dir, temp_output_dir):
        """
        Comprehensive test processing entire testFile directory.
        Marked as 'slow' - only run with: pytest -m slow
        """
        from ocr_toolkit.processors.excel_processor import ExcelDataProcessor
        from ocr_toolkit.processors.ocr_processor import OCRProcessor
        from ocr_toolkit.utils.file_discovery import discover_files
        from ocr_toolkit.utils.model_loader import load_ocr_model

        # Discover all supported files (excluding output/temp directories manually)
        all_files, base_dir, _ = discover_files(str(testfile_dir))

        # Filter out unwanted directories
        exclude_paths = ["markdown_output", "nested_test_structure", ".tmp"]
        files = [f for f in all_files if not any(excl in f for excl in exclude_paths)]

        print(f"\nFound {len(files)} files in testFile directory")

        # Initialize processors
        ocr_model = load_ocr_model("db_resnet50", "crnn_vgg16_bn", use_cpu=False)
        ocr_processor = OCRProcessor(ocr_model)
        excel_processor = ExcelDataProcessor()

        results = {"total": len(files), "success": 0, "failed": 0, "by_type": {}}

        start_time = time.time()

        for file_path in files:
            file_ext = Path(file_path).suffix.lower()
            file_name = Path(file_path).name

            try:
                if file_ext in [".xlsx", ".xls"]:
                    result = excel_processor.process(file_path)
                else:
                    result = ocr_processor.process(file_path, fast=True, pages="1-2")

                if result.success:
                    results["success"] += 1
                    print(f"  [OK] {file_name} ({file_ext})")
                else:
                    results["failed"] += 1
                    print(f"  [FAIL] {file_name} ({file_ext}): {result.error}")

                # Track by type
                if file_ext not in results["by_type"]:
                    results["by_type"][file_ext] = {"success": 0, "failed": 0}

                if result.success:
                    results["by_type"][file_ext]["success"] += 1
                else:
                    results["by_type"][file_ext]["failed"] += 1

            except Exception as e:
                results["failed"] += 1
                print(f"  [FAIL] {file_name} ({file_ext}): Exception - {e}")

        total_time = time.time() - start_time

        # Print summary
        print(f"\n{'=' * 60}")
        print("Full TestFile Processing Summary")
        print(f"{'=' * 60}")
        print(f"Total files: {results['total']}")
        print(f"Successful: {results['success']}")
        print(f"Failed: {results['failed']}")
        print(f"Success rate: {results['success'] / results['total'] * 100:.1f}%")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg per file: {total_time / results['total']:.2f}s")
        print("\nBy file type:")
        for ext, stats in sorted(results["by_type"].items()):
            total_type = stats["success"] + stats["failed"]
            print(f"  {ext}: {stats['success']}/{total_type} successful")
        print(f"{'=' * 60}\n")

        # Test assertions
        assert results["success"] > 0, "Should successfully process at least some files"
        assert results["success"] / results["total"] >= 0.5, "Success rate should be >= 50%"
