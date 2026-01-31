"""
PaddleOCR-VL-1.5 handler for advanced document structure analysis.

This module provides a handler for PaddleOCR-VL-1.5, which is a 0.9B VLM
for robust document parsing with support for:
- Text spotting (text-line localization and recognition)
- Table recognition
- Formula recognition
- Chart recognition
- Seal recognition
- Multi-language document parsing
- Irregular-shaped localization (polygonal detection)
"""

import logging
import os
import sys
import tempfile
import shutil
from pathlib import Path
from contextlib import redirect_stderr
from io import StringIO

# IMPORTANT: Set environment variables and logging levels BEFORE any PaddlePaddle imports
# to suppress noisy output during initialization
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['PADDLE_SDK_CHECK_CONNECTIVITY'] = 'False'
os.environ['GLOG_MINLOGLEVEL'] = '3'  # Only show FATAL errors
os.environ['GLOG_V'] = '0'  # Set verbosity to 0
os.environ['FLAGS_logtostderr'] = '0'  # Don't log to stderr

from ..utils.profiling import Profiler
from ..utils.model_loader import setup_nvidia_dll_paths

# Suppress PaddleX and PaddlePaddle logging (after utils import to avoid circular dependency)
logging.getLogger('paddlex').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('Paddle').setLevel(logging.ERROR)


class PaddleOCRVLHandler:
    """
    Handler for PaddleOCR-VL-1.5 document parsing.

    This class encapsulates PaddleOCR-VL-1.5 functionality for intelligent
    document analysis with vision-language models.
    """

    def __init__(self, use_gpu: bool = True, model_name: str = "PaddleOCR-VL-1.5", with_images: bool = False):
        """
        Initialize PaddleOCR-VL-1.5 handler.

        Args:
            use_gpu: Whether to use GPU for processing (default: True)
            model_name: Model name to use (default: "PaddleOCR-VL-1.5")
                       Options: "PaddleOCR-VL-1.5", "PaddleOCR-VL", or custom path
            with_images: Whether to extract and save images with links (default: False)
        """
        self.use_gpu = use_gpu
        self.model_name = model_name
        self.with_images = with_images
        self.logger = logging.getLogger(__name__)
        self.pipeline = None
        self.initialized = False

        # Initialize pipeline
        self._initialize()

    def _initialize(self) -> bool:
        """
        Initialize PaddleOCR-VL pipeline.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.logger.info(f"Initializing PaddleOCR-VL with model: {self.model_name}")

            # Special handling for Windows to find NVIDIA DLLs from pip packages
            setup_nvidia_dll_paths()

            # Suppress noisy PaddleX output by redirecting stderr during initialization
            from contextlib import redirect_stderr
            from io import StringIO

            stderr_capture = StringIO()
            with redirect_stderr(stderr_capture):
                # Import PaddleOCR
                from paddleocr import PaddleOCRVL
                import paddle

                # Set device based on use_gpu parameter
                if self.use_gpu:
                    try:
                        paddle.set_device('gpu')
                        self.logger.info("Using GPU for PaddleOCR-VL")
                    except Exception as e:
                        self.logger.warning(f"Failed to set GPU device: {e}. Falling back to CPU.")
                        paddle.set_device('cpu')
                        self.use_gpu = False
                else:
                    paddle.set_device('cpu')
                    self.logger.info("Using CPU for PaddleOCR-VL")

                # Initialize the pipeline with device configuration
                self.pipeline = PaddleOCRVL()

            self.initialized = True
            self.logger.info("PaddleOCR-VL initialized successfully")
            return True

        except ImportError:
            self.logger.error(
                "PaddleOCR-VL not available. "
                "Install with: pip install 'paddleocr[doc-parser]'"
            )
            self.initialized = False
            return False

        except Exception as e:
            self.logger.error(f"PaddleOCR-VL initialization failed: {e}")
            self.initialized = False
            return False

    def is_available(self) -> bool:
        """
        Check if PaddleOCR-VL is available and initialized.

        Returns:
            True if pipeline is ready to use, False otherwise
        """
        return self.initialized and self.pipeline is not None

    def process_document(
        self,
        file_path: str,
        *,
        output_dir: str | None = None,
        pages: str | None = None,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process document with PaddleOCR-VL.

        Args:
            file_path: Path to the document (PDF or image)
            output_dir: Directory to save extracted images (optional)
            pages: Optional page selection (e.g., "1-3,5,7-9")
            profiler: Optional profiler for performance tracking

        Returns:
            Tuple of (markdown_content, metadata)

        Raises:
            RuntimeError: If pipeline is not initialized
            ValueError: If page selection is invalid
        """
        if not self.is_available():
            raise RuntimeError("PaddleOCR-VL is not initialized")

        self._output_dir = output_dir
        ext = Path(file_path).suffix.lower()

        # For PDF files with page selection, we need to extract specific pages
        if ext == '.pdf' and pages:
            return self._process_pdf_with_page_selection(
                file_path, pages, profiler
            )

        # Process single document (image or PDF)
        return self._process_single_document(file_path, profiler)

    def _process_single_document(
        self,
        file_path: str,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process single document with PaddleOCR-VL.

        Args:
            file_path: Path to the document
            profiler: Optional profiler

        Returns:
            Tuple of (markdown_content, metadata)
        """
        if profiler:
            with profiler.track("paddleocr_vl_predict"):
                output = self.pipeline.predict(file_path)
        else:
            output = self.pipeline.predict(file_path)

        return self._extract_output(output, file_path)

    def _process_pdf_with_page_selection(
        self,
        pdf_path: str,
        pages: str,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict]:
        """
        Process PDF with specific page selection.

        Args:
            pdf_path: Path to the PDF file
            pages: Page selection string (e.g., "1-3,5,7-9")
            profiler: Optional profiler

        Returns:
            Tuple of (markdown_content, metadata)
        """
        from ..utils.page_selection import parse_pages_arg
        import pypdfium2 as pdfium

        # Parse page selection
        parsed_pages = parse_pages_arg(pages)

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

        # Process each selected page
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
                    with profiler.track("paddleocr_vl_predict_page"):
                        page_output = self.pipeline.predict(temp_image)
                else:
                    page_output = self.pipeline.predict(temp_image)

                page_md, _ = self._extract_output(page_output, pdf_path)

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
        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'engine': 'paddleocr_vl',
        }

        markdown_content = ""

        # PaddleOCR-VL returns result objects with save_to_markdown method
        if hasattr(output, '__iter__') and not isinstance(output, (str, dict)):
            # Handle iterable output (list of results)
            for result in output:
                markdown_content += self._extract_single_result(result)
        else:
            # Single result
            markdown_content = self._extract_single_result(output)

        return markdown_content, metadata

    def _extract_single_result(self, result) -> str:
        """
        Extract markdown from a single result object.

        Args:
            result: Single result from PaddleOCR-VL

        Returns:
            Extracted markdown content
        """
        # Check for save_to_markdown method
        if hasattr(result, 'save_to_markdown'):
            # Create temp directory and save markdown
            temp_dir = tempfile.mkdtemp()
            try:
                result.save_to_markdown(save_path=temp_dir)

                # Find the generated markdown file
                md_files = [f for f in os.listdir(temp_dir) if f.endswith('.md')]
                if md_files:
                    md_path = os.path.join(temp_dir, md_files[0])
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Handle images based on with_images setting
                    imgs_dir = os.path.join(temp_dir, 'imgs')
                    if self.with_images and self._output_dir and os.path.exists(imgs_dir):
                        # Create a unique imgs subdirectory for this document
                        # Use a timestamp-based directory name to avoid conflicts
                        import time
                        timestamp = str(int(time.time() * 1000))
                        output_imgs_dir = os.path.join(self._output_dir, f'imgs_{timestamp}')
                        os.makedirs(output_imgs_dir, exist_ok=True)

                        # Copy all images
                        img_files = []
                        for img_file in os.listdir(imgs_dir):
                            src = os.path.join(imgs_dir, img_file)
                            dst = os.path.join(output_imgs_dir, img_file)
                            shutil.copy2(src, dst)
                            img_files.append(img_file)
                            self.logger.debug(f"Copied image: {img_file}")

                        # Update markdown content to reference the new image directory
                        if img_files:
                            content = content.replace('imgs/', f'imgs_{timestamp}/')
                            metadata = {
                                'extracted_images': len(img_files),
                                'images_dir': f'imgs_{timestamp}',
                            }
                            # Store metadata for later reference
                            if hasattr(self, '_image_metadata'):
                                self._image_metadata.append(metadata)
                            else:
                                self._image_metadata = [metadata]
                    else:
                        # Remove image links from markdown (text-only mode)
                        import re
                        # Remove markdown image syntax: ![alt](path)
                        content = re.sub(r'!\[.*?\]\([^)]+\)', '', content)
                        # Remove inline image references if any
                        content = re.sub(r'<img[^>]*>', '', content)

                    return content

                # Fallback to parsing the result dict
                return self._parse_result_dict(result)
            finally:
                # Clean up temp directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

        # Check if result is a dict with parsing_res_list
        if isinstance(result, dict) and 'parsing_res_list' in result:
            return self._parse_parsing_res_list(result['parsing_res_list'])

        # Check for rec_texts attribute (text recognition results)
        if hasattr(result, 'rec_texts'):
            texts = result.rec_texts
            if isinstance(texts, list):
                return "\n".join(texts)
            return str(texts)

        # Check for data attribute
        if hasattr(result, 'data'):
            data = result.data
            if isinstance(data, dict):
                if 'parsing_res_list' in data:
                    return self._parse_parsing_res_list(data['parsing_res_list'])
                return data.get('markdown', data.get('text', str(data)))
            return str(data)

        # Dict-like object
        if hasattr(result, 'get'):
            if result.get('parsing_res_list'):
                return self._parse_parsing_res_list(result['parsing_res_list'])
            return result.get('markdown', result.get('text', str(result)))

        # Fallback: convert to string
        return str(result)

    def set_output_dir(self, output_dir: str):
        """Set the output directory for extracted images."""
        self._output_dir = output_dir

    def _parse_parsing_res_list(self, parsing_res_list: list) -> str:
        """
        Parse PaddleOCR-VL parsing_res_list into markdown format.

        Args:
            parsing_res_list: List of parsed elements from PaddleOCR-VL

        Returns:
            Formatted markdown content
        """
        if not parsing_res_list:
            return ""

        markdown_parts = []

        for item in parsing_res_list:
            if isinstance(item, str):
                # Simple string content
                markdown_parts.append(item)
            elif isinstance(item, dict):
                # Dict with content, bbox, label info
                label = item.get('label', 'text')
                content = item.get('content', '')

                if content:
                    # Format based on label type
                    if label == 'table':
                        markdown_parts.append(f"\\n{content}\\n")
                    elif label == 'formula':
                        markdown_parts.append(f"$${content}$$")
                    elif label == 'title' or label == 'header':
                        markdown_parts.append(f"# {content}")
                    else:
                        # Default text
                        markdown_parts.append(content)

        return "\n\n".join(markdown_parts)

    def _parse_result_dict(self, result) -> str:
        """
        Parse result dict into markdown format.

        Args:
            result: Result dict from PaddleOCR-VL

        Returns:
            Formatted markdown content
        """
        # Try to access the dict representation
        if hasattr(result, '__dict__'):
            d = result.__dict__
            if 'parsing_res_list' in d:
                return self._parse_parsing_res_list(d['parsing_res_list'])

        # Fallback
        return str(result)
