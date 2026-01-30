"""
PaddleOCR 3.x handler for advanced OCR processing.

This module provides a high-cohesion handler for PaddleOCR 3.x initialization
and document processing with support for:
- Multi-language OCR (109 languages)
- Document orientation classification
- Text unwarping
- Multi-page PDF processing
- Page selection
"""

import logging
import os
from pathlib import Path

from ..utils.profiling import Profiler


class PaddleOCRHandler:
    """
    Handler for PaddleOCR 3.x document processing.

    This class encapsulates all PaddleOCR 3.x functionality including:
    - Model initialization and configuration
    - Single image and multi-page PDF processing
    - Text extraction with layout preservation
    - Page selection support
    """

    def __init__(self, use_gpu: bool = True, lang: str = 'en'):
        """
        Initialize PaddleOCR handler.

        Args:
            use_gpu: Whether to use GPU for processing (default: True) - Note: PaddleOCR 3.x auto-detects GPU
            lang: Language code for OCR (default: 'en', options: 'ch', 'en', 'fr', 'ger', 'kor', 'japan', etc.)
        """
        self.use_gpu = use_gpu  # Stored for reference but not used in initialization
        self.lang = lang
        self.logger = logging.getLogger(__name__)
        self.pipeline = None
        self.initialized = False

        # Disable model source check warnings
        os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

        # Initialize PaddleOCR
        self._initialize()

    def _initialize(self) -> bool:
        """
        Initialize PaddleOCR pipeline.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.logger.info("Initializing PaddleOCR 3.x for document processing...")

            # Import PaddleOCR
            from paddleocr import PaddleOCR

            # Initialize the pipeline
            # PaddleOCR 3.x auto-detects GPU/CPU, uses 'lang' for language
            self.pipeline = PaddleOCR(lang=self.lang)

            self.initialized = True
            self.logger.info("PaddleOCR 3.x initialized successfully")
            return True

        except ImportError:
            self.logger.error("PaddleOCR not available. Please install paddleocr>=3.0.0")
            self.initialized = False
            return False

        except Exception as e:
            self.logger.error(f"PaddleOCR initialization failed: {e}")
            self.initialized = False
            return False

    def is_available(self) -> bool:
        """
        Check if PaddleOCR is available and initialized.

        Returns:
            True if PaddleOCR is ready to use, False otherwise
        """
        return self.initialized and self.pipeline is not None

    def process_document(
        self,
        file_path: str,
        *,
        pages: str | None = None,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process document with PaddleOCR-VL.

        Args:
            file_path: Path to the document (PDF or image)
            pages: Optional page selection (e.g., "1-3,5,7-9")
            profiler: Optional profiler for performance tracking

        Returns:
            Tuple of (markdown_content, metadata)

        Raises:
            RuntimeError: If PaddleOCR-VL is not initialized
            ValueError: If page selection is invalid
        """
        if not self.is_available():
            raise RuntimeError("PaddleOCR-VL is not initialized")

        ext = Path(file_path).suffix.lower()

        # Parse page selection if provided
        parsed_pages = None
        if pages:
            from ..utils.page_selection import parse_pages_arg
            parsed_pages = parse_pages_arg(pages)

        # For PDF files with page selection, we need to extract specific pages
        if ext == '.pdf' and parsed_pages is not None:
            return self._process_pdf_with_page_selection(
                file_path, parsed_pages, profiler=profiler
            )

        # Process entire document (PDF or image)
        return self._process_full_document(file_path, profiler=profiler)

    def _process_full_document(
        self,
        file_path: str,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process full document without page selection.

        Args:
            file_path: Path to the document
            profiler: Optional profiler

        Returns:
            Tuple of (markdown_content, metadata)
        """
        if profiler:
            with profiler.track("paddleocr_predict"):
                output = self.pipeline.predict(file_path)
        else:
            output = self.pipeline.predict(file_path)

        # Extract markdown content and metadata
        return self._extract_output(output, file_path)

    def _process_pdf_with_page_selection(
        self,
        pdf_path: str,
        parsed_pages,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process PDF with specific page selection.

        Args:
            pdf_path: Path to the PDF file
            parsed_pages: Parsed page selection object
            profiler: Optional profiler

        Returns:
            Tuple of (markdown_content, metadata)
        """
        import pypdfium2 as pdfium

        # Get total pages
        pdf = pdfium.PdfDocument(pdf_path)
        try:
            total_pages = len(pdf)
            requested = parsed_pages.indices
            page_indices = [i for i in requested if 0 <= i < total_pages]

            if not page_indices:
                raise ValueError(f"No valid pages selected (total pages: {total_pages})")

            self.logger.info(f"Processing {len(page_indices)} pages from PDF")
        finally:
            pdf.close()

        # For page selection, PaddleOCR-VL needs individual images
        # We'll process each selected page and combine results
        markdown_pages = []
        metadata = {
            'total_pages': total_pages,
            'selected_pages': page_indices,
            'page_count': len(page_indices),
        }

        for page_idx in page_indices:
            # Extract single page to temp image
            temp_image = self._extract_page_to_image(pdf_path, page_idx)

            try:
                if profiler:
                    with profiler.track("paddleocr_predict_page"):
                        page_output = self.pipeline.predict(temp_image)
                else:
                    page_output = self.pipeline.predict(temp_image)

                page_md, page_meta = self._extract_output(page_output, pdf_path)

                # Add page header
                page_number = page_idx + 1
                page_content = f"## Page {page_number}\n\n{page_md}"
                markdown_pages.append(page_content)

            finally:
                # Clean up temp image
                if os.path.exists(temp_image):
                    os.remove(temp_image)

        combined_markdown = "\n\n".join(markdown_pages)
        return combined_markdown, metadata

    def _extract_page_to_image(self, pdf_path: str, page_idx: int) -> str:
        """
        Extract a single page from PDF to a temporary image file.

        Args:
            pdf_path: Path to the PDF
            page_idx: Page index (0-based)

        Returns:
            Path to the temporary image file
        """
        import tempfile
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_path)
        try:
            page = pdf[page_idx]
            # Render at scale 2.0 for good quality
            bitmap = page.render(scale=2.0)

            # Convert to PIL Image and save to temp file
            pil_image = bitmap.to_pil()
            fd, temp_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)

            pil_image.save(temp_path)
            return temp_path

        finally:
            pdf.close()

    def _extract_output(self, output, file_path: str) -> tuple[str, dict]:
        """
        Extract markdown content and metadata from PaddleOCR-VL output.

        Args:
            output: Raw output from PaddleOCR-VL
            file_path: Original file path

        Returns:
            Tuple of (markdown_content, metadata)
        """
        # PaddleOCR-VL returns structured output with OCR results
        # The output format may vary based on version, handle both cases

        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
        }

        # Extract markdown based on output format
        if isinstance(output, dict):
            # Newer format: dict with keys
            markdown_content = self._format_dict_output(output, metadata)
        elif isinstance(output, list):
            # List format: multiple pages or results
            markdown_content = self._format_list_output(output, metadata)
        elif isinstance(output, str):
            # Direct markdown output
            markdown_content = output
        else:
            # Fallback: convert to string
            self.logger.warning(f"Unknown PaddleOCR-VL output format: {type(output)}")
            markdown_content = str(output)

        return markdown_content, metadata

    def _format_dict_output(self, output: dict, metadata: dict) -> str:
        """
        Format dict output from PaddleOCR-VL to markdown.

        Args:
            output: Dict output from PaddleOCR-VL
            metadata: Metadata dict to update

        Returns:
            Formatted markdown content
        """
        markdown_parts = []

        # Check for common keys in PaddleOCR-VL output
        if 'markdown' in output:
            markdown_parts.append(output['markdown'])

        if 'text' in output:
            markdown_parts.append(output['text'])

        if 'ocr_results' in output:
            # Process structured OCR results
            ocr_results = output['ocr_results']
            if isinstance(ocr_results, list):
                for page_result in ocr_results:
                    if isinstance(page_result, dict):
                        if 'text' in page_result:
                            markdown_parts.append(page_result['text'])
                        if 'table' in page_result:
                            # Table in markdown format
                            markdown_parts.append(page_result['table'])
                        if 'formula' in page_result:
                            # Formula in LaTeX format
                            formula = page_result['formula']
                            markdown_parts.append(f"$${formula}$$")

        # Update metadata with available info
        for key in ['page_count', 'language', 'table_count', 'formula_count']:
            if key in output:
                metadata[key] = output[key]

        return "\n\n".join(markdown_parts) if markdown_parts else ""

    def _format_list_output(self, output: list, metadata: dict) -> str:
        """
        Format list output from PaddleOCR 3.x to markdown.

        Args:
            output: List output from PaddleOCR 3.x
            metadata: Metadata dict to update

        Returns:
            Formatted markdown content
        """
        markdown_parts = []

        for item in output:
            if isinstance(item, dict):
                # PaddleOCR 3.x returns dict with rec_texts (recognized texts)
                if 'rec_texts' in item:
                    texts = item['rec_texts']
                    if isinstance(texts, list):
                        # Join text lines with newlines for better readability
                        markdown_parts.append("\n".join(texts))
                    else:
                        markdown_parts.append(str(texts))

                # Also check for other possible keys
                if 'markdown' in item:
                    markdown_parts.append(item['markdown'])
                elif 'text' in item:
                    markdown_parts.append(item['text'])
                elif 'table' in item:
                    markdown_parts.append(item['table'])
                elif 'formula' in item:
                    formula = item['formula']
                    markdown_parts.append(f"$${formula}$$")
            elif isinstance(item, str):
                markdown_parts.append(item)

        metadata['page_count'] = len(output)
        return "\n\n".join(markdown_parts) if markdown_parts else ""

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported languages.

        Returns:
            List of supported language codes
        """
        # PaddleOCR-VL supports 109+ languages
        # This is a subset of commonly used languages
        return [
            'ch',  # Chinese
            'en',  # English
            'fr',  # French
            'ger', # German
            'kor', # Korean
            'japan', # Japanese
            'ru',  # Russian
            'ar',  # Arabic
            'es',  # Spanish
            'it',  # Italian
            'pt',  # Portuguese
            # And 90+ more languages supported
        ]
