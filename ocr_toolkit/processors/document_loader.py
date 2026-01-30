"""
Document loader for OCR processing.

This module provides a high-cohesion loader for various document formats,
handling format detection, conversion, and loading into DocumentFile objects.
"""

import logging
from pathlib import Path
from doctr.io import DocumentFile

from ..converters import get_office_converter
from ..utils import get_path_normalizer
from ..utils.page_selection import parse_pages_arg
from ..utils.profiling import Profiler
from .base import ProcessingResult


class DocumentLoader:
    """
    Handler for loading documents of various formats.

    This class encapsulates document loading logic including:
    - Format detection and validation
    - Path normalization for cross-platform compatibility
    - Office document to PDF conversion
    - Image and PDF loading
    """

    # Supported formats grouped by type
    PDF_FORMATS = {'.pdf'}
    IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
    OFFICE_FORMATS = {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}
    TEXT_FORMATS = {'.txt', '.md', '.rtf'}

    DEFAULT_PDF_RENDER_SCALE = 2.0  # 2.0 => 144dpi (pypdfium2 uses 72dpi at scale=1)
    FAST_PDF_RENDER_SCALE = 1.5
    FAST_MAX_IMAGE_SIDE = 2000

    def __init__(self):
        """Initialize document loader with required utilities."""
        self.logger = logging.getLogger(__name__)
        self.office_converter = get_office_converter()
        self.path_normalizer = get_path_normalizer()

    @classmethod
    def get_supported_formats(cls) -> list[str]:
        """
        Get list of all supported file formats.

        Returns:
            List of supported file extensions (lowercase, with dot)
        """
        all_formats = (
            cls.PDF_FORMATS |
            cls.IMAGE_FORMATS |
            cls.OFFICE_FORMATS |
            cls.TEXT_FORMATS
        )
        return sorted(all_formats)

    @classmethod
    def is_supported_format(cls, file_extension: str) -> bool:
        """
        Check if the given file format is supported.

        Args:
            file_extension: File extension to check (with or without dot)

        Returns:
            True if format is supported, False otherwise
        """
        ext = file_extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext

        return ext in cls.get_supported_formats()

    @classmethod
    def is_text_format(cls, file_extension: str) -> bool:
        """
        Check if the given file format is a text format.

        Args:
            file_extension: File extension to check

        Returns:
            True if format is a text format, False otherwise
        """
        return file_extension.lower() in cls.TEXT_FORMATS

    def load_document(
        self,
        file_path: str,
        result: ProcessingResult | None = None,
        *,
        pages: str | None = None,
        fast: bool = False,
        profiler: Profiler | None = None,
    ) -> DocumentFile | None:
        """
        Load document file for OCR processing.

        Args:
            file_path: Path to the document
            result: Optional ProcessingResult to update with temp files and errors

        Returns:
            DocumentFile object or None if loading failed
        """
        try:
            ext = Path(file_path).suffix.lower()

            # Validate format
            if not self.is_supported_format(ext):
                error_msg = f'Unsupported file format: {ext}'
                self.logger.error(error_msg)
                if result:
                    result.error = error_msg
                return None

            # Handle Chinese path encoding issues on Windows
            normalized_path = self.path_normalizer.normalize_path(file_path)

            # Load based on format type
            if ext in self.PDF_FORMATS:
                return self._load_pdf(normalized_path, pages=pages, fast=fast, result=result, profiler=profiler)

            elif ext in self.IMAGE_FORMATS:
                return self._load_image(normalized_path, fast=fast, result=result, profiler=profiler)

            elif ext in self.OFFICE_FORMATS:
                return self._load_office_document(
                    normalized_path,
                    file_path,
                    result,
                    pages=pages,
                    fast=fast,
                    profiler=profiler,
                )

            else:
                error_msg = f'Unsupported format for document loading: {ext}'
                self.logger.error(error_msg)
                if result:
                    result.error = error_msg
                return None

        except Exception as e:
            error_msg = f'Failed to load document: {str(e)}'
            self.logger.error(f"{error_msg} - {file_path}")
            if result:
                result.error = error_msg
            return None

    def _load_pdf(
        self,
        normalized_path: str,
        *,
        pages: str | None = None,
        fast: bool = False,
        result: ProcessingResult | None = None,
        profiler: Profiler | None = None,
    ) -> DocumentFile:
        """
        Load PDF document.

        Args:
            normalized_path: Normalized file path

        Returns:
            DocumentFile loaded from PDF
        """
        parsed_pages = parse_pages_arg(pages)
        if parsed_pages is None and not fast:
            if profiler:
                with profiler.track("load_pdf_doctr"):
                    doc = DocumentFile.from_pdf(normalized_path)
            else:
                doc = DocumentFile.from_pdf(normalized_path)
            page_numbers = list(range(1, len(doc) + 1))
            pdf_total_pages = len(doc)
            render_scale = self.DEFAULT_PDF_RENDER_SCALE
        else:
            render_scale = self.FAST_PDF_RENDER_SCALE if fast else self.DEFAULT_PDF_RENDER_SCALE
            if profiler:
                with profiler.track("load_pdf_pdfium"):
                    doc, page_numbers, pdf_total_pages = self._render_pdf_with_pdfium(
                        normalized_path, parsed_pages, render_scale
                    )
            else:
                doc, page_numbers, pdf_total_pages = self._render_pdf_with_pdfium(
                    normalized_path, parsed_pages, render_scale
                )

        if result:
            result.metadata["page_numbers"] = page_numbers
            result.metadata["pdf_total_pages"] = pdf_total_pages
            result.metadata["pdf_render_scale"] = render_scale
            result.metadata["fast_mode"] = bool(fast)

        self.logger.debug(f"Loaded PDF with {len(doc)} pages")
        return doc

    def _load_image(
        self,
        normalized_path: str,
        *,
        fast: bool = False,
        result: ProcessingResult | None = None,
        profiler: Profiler | None = None,
    ) -> DocumentFile:
        """
        Load image file.

        Args:
            normalized_path: Normalized file path

        Returns:
            DocumentFile loaded from image
        """
        if profiler:
            with profiler.track("load_image"):
                doc = DocumentFile.from_images([normalized_path])
        else:
            doc = DocumentFile.from_images([normalized_path])

        if fast and doc:
            if profiler:
                with profiler.track("downscale_image", count=len(doc)):
                    doc = [self._maybe_downscale_numpy_image(img) for img in doc]
            else:
                doc = [self._maybe_downscale_numpy_image(img) for img in doc]

        if result:
            result.metadata["page_numbers"] = [1]
            result.metadata["fast_mode"] = bool(fast)

        self.logger.debug("Loaded image for processing")
        return doc

    def _load_office_document(self, normalized_path: str, original_path: str,
                             result: ProcessingResult | None = None,
                             *,
                             pages: str | None = None,
                             fast: bool = False,
                             profiler: Profiler | None = None) -> DocumentFile | None:
        """
        Load Office document by converting to PDF first.

        Args:
            normalized_path: Normalized file path
            original_path: Original file path (for error messages)
            result: Optional ProcessingResult to update with temp files

        Returns:
            DocumentFile loaded from converted PDF, or None if conversion failed
        """
        # Convert Office document to PDF first
        if profiler:
            with profiler.track("office_to_pdf"):
                temp_pdf = self.office_converter.create_temp_pdf(normalized_path)
        else:
            temp_pdf = self.office_converter.create_temp_pdf(normalized_path)

        if not temp_pdf:
            error_msg = f'Failed to convert Office document to PDF: {original_path}'
            self.logger.error(error_msg)
            if result:
                result.error = error_msg
            return None

        # Track temp file for cleanup
        if result:
            result.temp_files.append(temp_pdf)
            result.metadata["converted_format"] = ".pdf"

        # Load the converted PDF
        doc = self._load_pdf(temp_pdf, pages=pages, fast=fast, result=result, profiler=profiler)
        self.logger.debug(f"Converted Office document to PDF with {len(doc)} pages")
        return doc

    def _render_pdf_with_pdfium(
        self,
        pdf_path: str,
        parsed_pages,
        render_scale: float,
    ) -> tuple[list, list[int], int]:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_path)
        try:
            pdf_total_pages = len(pdf)
            if parsed_pages is None:
                page_indices = list(range(pdf_total_pages))
            else:
                requested = parsed_pages.indices
                page_indices = [i for i in requested if 0 <= i < pdf_total_pages]

            if not page_indices:
                raise ValueError(f"No valid pages selected for PDF (total pages: {pdf_total_pages})")

            page_numbers = [i + 1 for i in page_indices]

            pages = []
            for idx in page_indices:
                page = pdf[idx]
                bitmap = page.render(scale=render_scale, rev_byteorder=True)
                img = bitmap.to_numpy()
                pages.append(self._maybe_downscale_numpy_image(img) if render_scale and render_scale < 2.0 else img)

            return pages, page_numbers, pdf_total_pages
        finally:
            pdf.close()

    def _maybe_downscale_numpy_image(self, img):
        """
        Downscale large images in fast mode to reduce OCR workload.

        Keeps aspect ratio and caps the longest side at FAST_MAX_IMAGE_SIDE.
        """
        try:
            height, width = img.shape[:2]
        except Exception:
            return img

        max_side = max(height, width)
        if max_side <= self.FAST_MAX_IMAGE_SIDE:
            return img

        try:
            import numpy as np
            from PIL import Image

            scale = self.FAST_MAX_IMAGE_SIDE / max_side
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))

            pil = Image.fromarray(img)
            pil = pil.resize((new_w, new_h), resample=Image.BILINEAR)
            return np.asarray(pil)
        except Exception:
            return img
