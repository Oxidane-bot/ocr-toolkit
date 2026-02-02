"""
OCR processor implementation using the abstract base class.

This module provides a clean, reusable OCR processor that follows
the FileProcessorBase interface for consistent behavior.

The processor has been refactored following high-cohesion, low-coupling principles:
- PaddleOCR 3.x handling: paddleocr_handler.py
- Document loading: document_loader.py
- Text file processing: text_file_processor.py
- Excel data extraction: excel_processor.py
"""

import logging
import time
from pathlib import Path

from ..utils import get_temp_manager
from ..utils.profiling import Profiler
from .base import FileProcessorBase, ProcessingResult
from .document_loader import DocumentLoader
from .excel_processor import ExcelDataProcessor
from .paddleocr_handler import PaddleOCRHandler
from .text_file_processor import TextFileProcessor


def cleanup_temp_files(paths: list[str]) -> None:
    """Safely delete a list of temporary files, ignoring errors."""
    temp_manager = get_temp_manager()
    for path in paths or []:
        temp_manager.cleanup_file(path)


class OCRProcessor(FileProcessorBase):
    """
    OCR processor implementation using PaddleOCR 3.x.

    This processor handles OCR processing for PDFs, images, Office documents,
    and text files with proper temporary file management and error handling.

    Architecture:
    - Delegates document loading to DocumentLoader
    - Delegates text file processing to TextFileProcessor
    - Delegates Excel data extraction to ExcelDataProcessor
    - Uses PaddleOCR 3.x for OCR processing
    - Coordinates overall processing workflow
    """

    def __init__(self, batch_size: int = 1, use_gpu: bool = True, use_direct_excel: bool = True):
        """
        Initialize OCR processor.

        Args:
            batch_size: Number of pages to process in each batch (for compatibility)
            use_gpu: Whether to use GPU for PaddleOCR processing
            use_direct_excel: Whether to use direct Excel data extraction (faster, no Excel install needed)
        """
        super().__init__()
        self.batch_size = batch_size
        self.use_gpu = use_gpu
        self.logger = logging.getLogger(__name__)
        self.temp_manager = get_temp_manager()

        # Initialize specialized handlers
        self.document_loader = DocumentLoader()
        self.text_processor = TextFileProcessor()

        # Initialize Excel data processor if requested
        self.excel_processor = None
        self.use_direct_excel = use_direct_excel
        if use_direct_excel:
            self.excel_processor = ExcelDataProcessor()

        # Initialize PaddleOCR handler
        self.paddleocr_handler = PaddleOCRHandler(use_gpu=use_gpu)

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats for OCR processing."""
        return DocumentLoader.get_supported_formats()

    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        return DocumentLoader.is_supported_format(file_extension)

    def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """
        Process document with OCR.

        Args:
            file_path: Path to the document
            **kwargs: Additional processing parameters

        Returns:
            ProcessingResult object with processing results
        """
        start_time = time.time()
        result = self._create_result(file_path, "ocr", start_time)

        fast = bool(kwargs.get("fast", False))
        pages = kwargs.get("pages")
        profile_enabled = bool(kwargs.get("profile", False))
        profiler = Profiler() if profile_enabled else None

        if not self._validate_file(file_path):
            result.error = f"Invalid file: {file_path}"
            result.processing_time = time.time() - start_time
            return result

        try:
            ext = Path(file_path).suffix.lower()

            if not self.supports_format(ext):
                result.error = f"Unsupported file format for OCR: {ext}"
                result.processing_time = time.time() - start_time
                return result

            # Handle text files directly (no OCR needed)
            if self.text_processor.supports_format(ext):
                content = self.text_processor.process_file(file_path)
                result.content = content
                result.success = True
                result.pages = 1
                self.logger.debug(f"Processed text file {file_path} successfully")
                result.processing_time = time.time() - start_time
                return result

            # Handle Excel files with direct data extraction (if enabled)
            if self.excel_processor and self.excel_processor.supports_format(ext):
                excel_result = self.excel_processor.process(file_path)
                if excel_result.success:
                    # Use Excel extraction result
                    result.content = excel_result.content
                    result.success = True
                    result.pages = excel_result.pages
                    self.logger.debug(
                        f"Extracted data from {excel_result.pages} sheets in {file_path}"
                    )
                    result.processing_time = time.time() - start_time
                    return result
                else:
                    # Excel extraction failed, fall back to PDF conversion
                    self.logger.warning(
                        f"Excel data extraction failed for {file_path}: {excel_result.error}"
                    )
                    self.logger.info(f"Falling back to PDF conversion for {file_path}")

            # Process with PaddleOCR (handles PDFs and images directly)
            # For Office documents, they need to be converted to PDF first
            if ext in DocumentLoader.OFFICE_FORMATS:
                # Convert Office document to PDF first
                office_converter = self.document_loader.office_converter
                temp_pdf = office_converter.create_temp_pdf(file_path)

                if not temp_pdf:
                    result.error = f"Failed to convert Office document to PDF: {file_path}"
                    result.processing_time = time.time() - start_time
                    return result

                result.temp_files.append(temp_pdf)
                process_path = temp_pdf
            else:
                process_path = file_path

            # Process with PaddleOCR
            content, metadata = self.paddleocr_handler.process_document(
                process_path,
                pages=pages,
                profiler=profiler,
            )

            result.content = content
            result.success = True
            result.pages = metadata.get("page_count", 1)
            result.metadata.update(metadata)

            self.logger.debug(f"OCR processed {file_path} successfully with {result.pages} pages")

        except Exception as e:
            return self._handle_exception(e, result)

        finally:
            # Clean up temporary files
            if result.temp_files:
                cleanup_temp_files(result.temp_files)

        if profiler:
            result.metadata["profile"] = profiler.to_dict()

        result.processing_time = time.time() - start_time
        return result
