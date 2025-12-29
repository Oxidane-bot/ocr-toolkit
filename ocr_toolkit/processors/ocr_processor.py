"""
OCR processor implementation using the abstract base class.

This module provides a clean, reusable OCR processor that follows
the FileProcessorBase interface for consistent behavior.

The processor has been refactored following high-cohesion, low-coupling principles:
- CnOCR handling: cnocr_handler.py
- Document loading: document_loader.py
- Text file processing: text_file_processor.py
- Excel data extraction: excel_processor.py
"""

import logging
import os
import time
from pathlib import Path

from doctr.io import DocumentFile

from ..utils import get_temp_manager
from ..utils.profiling import Profiler
from .base import FileProcessorBase, ProcessingResult
from .cnocr_handler import CnOCRHandler
from .document_loader import DocumentLoader
from .excel_processor import ExcelDataProcessor
from .text_file_processor import TextFileProcessor


def cleanup_temp_files(paths: list[str]) -> None:
    """Safely delete a list of temporary files, ignoring errors."""
    temp_manager = get_temp_manager()
    for path in paths or []:
        temp_manager.cleanup_file(path)


class OCRProcessor(FileProcessorBase):
    """
    OCR processor implementation using DocTR and optionally CnOCR.

    This processor handles OCR processing for PDFs, images, Office documents,
    and text files with proper temporary file management and error handling.

    Architecture:
    - Delegates document loading to DocumentLoader
    - Delegates text file processing to TextFileProcessor
    - Delegates Excel data extraction to ExcelDataProcessor
    - Delegates CnOCR processing to CnOCRHandler
    - Handles DocTR OCR processing internally
    - Coordinates overall processing workflow
    """

    def __init__(self, ocr_model, batch_size: int = 16, use_cnocr: bool = False, use_direct_excel: bool = True):
        """
        Initialize OCR processor.

        Args:
            ocr_model: Loaded DocTR OCR model
            batch_size: Number of pages to process in each batch
            use_cnocr: Whether to use CnOCR for Chinese text recognition (better for Chinese documents)
            use_direct_excel: Whether to use direct Excel data extraction (faster, no Excel install needed)
        """
        super().__init__()
        self.ocr_model = ocr_model
        self.batch_size = batch_size
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

        # Initialize CnOCR handler if requested
        self.cnocr_handler = None
        self.use_cnocr = use_cnocr
        if use_cnocr:
            self._initialize_cnocr_handler()

    def _initialize_cnocr_handler(self) -> None:
        """Initialize CnOCR handler for Chinese text recognition."""
        try:
            self.cnocr_handler = CnOCRHandler(batch_size=self.batch_size)
            if not self.cnocr_handler.is_available():
                self.logger.warning("CnOCR handler initialized but not available, falling back to DocTR")
                self.use_cnocr = False
                self.cnocr_handler = None
        except Exception as e:
            self.logger.error(f"Failed to initialize CnOCR handler: {e}")
            self.logger.info("Falling back to DocTR for OCR processing")
            self.use_cnocr = False
            self.cnocr_handler = None

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
        result = self._create_result(file_path, 'ocr', start_time)

        fast = bool(kwargs.get("fast", False))
        pages = kwargs.get("pages", None)
        profile_enabled = bool(kwargs.get("profile", False))
        profiler = Profiler() if profile_enabled else None

        if not self._validate_file(file_path):
            result.error = f'Invalid file: {file_path}'
            result.processing_time = time.time() - start_time
            return result

        try:
            ext = Path(file_path).suffix.lower()

            if not self.supports_format(ext):
                result.error = f'Unsupported file format for OCR: {ext}'
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
                    self.logger.debug(f"Extracted data from {excel_result.pages} sheets in {file_path}")
                    result.processing_time = time.time() - start_time
                    return result
                else:
                    # Excel extraction failed, fall back to PDF conversion
                    self.logger.warning(f"Excel data extraction failed for {file_path}: {excel_result.error}")
                    self.logger.info(f"Falling back to PDF conversion for {file_path}")

            # Load document for OCR processing
            doc = self.document_loader.load_document(
                file_path,
                result,
                pages=pages,
                fast=fast,
                profiler=profiler,
            )
            if doc is None:
                result.processing_time = time.time() - start_time
                return result

            # Process with OCR (choose between CnOCR and DocTR)
            page_numbers = result.metadata.get("page_numbers")
            if self._should_use_cnocr(ext):
                content = self.cnocr_handler.process_document(
                    doc,
                    file_path,
                    ext,
                    page_numbers=page_numbers,
                    profiler=profiler,
                )
            else:
                content = self._process_with_doctr(
                    doc,
                    file_path,
                    ext,
                    page_numbers=page_numbers,
                    profiler=profiler,
                )

            result.content = content
            result.success = True
            result.pages = len(doc) if doc else 1

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

    def _should_use_cnocr(self, ext: str) -> bool:
        """
        Determine whether to use CnOCR for the given format.

        Args:
            ext: File extension

        Returns:
            True if CnOCR should be used, False otherwise
        """
        # Only use CnOCR if:
        # 1. CnOCR is enabled and available
        # 2. The format is supported by CnOCR (images and PDFs)
        if not self.use_cnocr or not self.cnocr_handler:
            return False

        cnocr_supported = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.pdf'}
        return ext in cnocr_supported

    def _process_with_doctr(
        self,
        doc: DocumentFile,
        file_path: str,
        ext: str,
        *,
        page_numbers: list[int] | None = None,
        profiler: Profiler | None = None,
    ) -> str:
        """
        Process loaded document with DocTR OCR model.

        Args:
            doc: Loaded DocumentFile
            file_path: Original file path
            ext: File extension

        Returns:
            Processed markdown content
        """
        markdown_content = []

        # Process in batches
        for i in range(0, len(doc), self.batch_size):
            batch = doc[i : i + self.batch_size]
            try:
                import torch
                inference_ctx = (
                    torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
                )
            except Exception:
                from contextlib import nullcontext
                inference_ctx = nullcontext()

            if profiler:
                with profiler.track("doctr_inference", count=len(batch)):
                    with inference_ctx:
                        ocr_result = self.ocr_model(batch)
            else:
                with inference_ctx:
                    ocr_result = self.ocr_model(batch)

            for page_idx, page_result in enumerate(ocr_result.pages):
                current_page_number = (
                    page_numbers[i + page_idx]
                    if page_numbers and (i + page_idx) < len(page_numbers)
                    else i + page_idx + 1
                )
                if profiler:
                    with profiler.track("doctr_render_text"):
                        text = page_result.render()
                else:
                    text = page_result.render()

                # Format content based on file type
                formatted_text = self._format_page_content(text, current_page_number, file_path, ext)
                markdown_content.append(formatted_text)

        return "\n\n".join(markdown_content)

    def _format_page_content(self, text: str, page_number: int, file_path: str, ext: str) -> str:
        """
        Format page content as markdown.

        Args:
            text: OCR extracted text
            page_number: Page number (1-based)
            file_path: Original file path
            ext: File extension

        Returns:
            Formatted markdown string
        """
        # For single images, use filename as header
        if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}:
            return f"# {os.path.basename(file_path)}\n\n{text}"

        # For multi-page documents, use page numbers
        return f"## Page {page_number}\n\n{text}"
