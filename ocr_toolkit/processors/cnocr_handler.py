"""
CnOCR handler for Chinese text recognition.

This module provides a high-cohesion handler for CnOCR initialization
and Chinese text processing with multi-threading support.
"""

import logging
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from doctr.io import DocumentFile


class CnOCRHandler:
    """
    Handler for CnOCR Chinese text recognition.

    This class encapsulates all CnOCR-specific functionality including:
    - Model initialization and configuration
    - Multi-threaded batch processing
    - Text extraction and formatting
    """

    def __init__(self, batch_size: int = 16, num_threads: int = 4):
        """
        Initialize CnOCR handler.

        Args:
            batch_size: Number of pages/images to process in each batch
            num_threads: Number of threads for parallel processing (optimal for GPU: 4)
        """
        self.batch_size = batch_size
        self.num_threads = num_threads
        self.logger = logging.getLogger(__name__)
        self.cnocr = None
        self.initialized = False

        # Initialize CnOCR
        self._initialize()

    def _initialize(self) -> bool:
        """
        Initialize CnOCR for Chinese text recognition.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            # Clear font path environment variable to avoid issues
            if 'FONTPATH' in os.environ:
                del os.environ['FONTPATH']

            # Fix PATH for huggingface-cli if we're in UV tool environment
            original_path = os.environ.get('PATH', '')
            script_dir = os.path.dirname(sys.executable)
            if script_dir not in original_path:
                os.environ['PATH'] = f"{script_dir};{original_path}"
                self.logger.debug(f"Added {script_dir} to PATH for huggingface-cli access")

            # Set UTF-8 encoding for Windows console to avoid Unicode errors
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONUTF8'] = '1'

            # Verify huggingface-cli is accessible
            hf_cli_path = shutil.which('huggingface-cli')
            if hf_cli_path:
                self.logger.debug(f"Found huggingface-cli at: {hf_cli_path}")
            else:
                self.logger.warning("huggingface-cli not found in PATH, CnOCR model download may fail")

            self.logger.info("Initializing CnOCR for Chinese text recognition...")

            # Import and initialize CnOCR
            from cnocr import CnOcr

            # Let CnOCR use default configuration and auto-select backend
            self.cnocr = CnOcr()

            # Debug: Check which backend CnOCR is actually using
            self._log_backend_info()

            self.initialized = True
            self.logger.info("CnOCR initialized successfully for Chinese text recognition")
            return True

        except ImportError:
            self.logger.warning("CnOCR not available, cannot use Chinese OCR")
            self.initialized = False
            return False

        except FileNotFoundError as e:
            if "huggingface-cli" in str(e):
                self.logger.error("CnOCR model download failed: huggingface-cli not found. "
                                "Please ensure huggingface-hub[cli] is installed.")
            else:
                self.logger.error(f"CnOCR model files missing: {e}")
            self.initialized = False
            return False

        except Exception as e:
            error_msg = str(e)
            if "does not exists" in error_msg or "onnx" in error_msg.lower():
                self.logger.error(f"CnOCR model download incomplete: {e}")
                self.logger.info("You may need to run: huggingface-cli download --help")
                self.logger.info("Or delete CnOCR cache and retry to force model re-download")
            else:
                self.logger.error(f"CnOCR initialization failed: {e}")
            self.initialized = False
            return False

    def _log_backend_info(self) -> None:
        """Log information about CnOCR backend configuration."""
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            self.logger.debug(f"CnOCR: Available providers: {providers}")

            # Check if CUDA is being used
            if hasattr(self.cnocr, 'det_model') and hasattr(self.cnocr.det_model, 'session'):
                det_providers = self.cnocr.det_model.session.get_providers()
                self.logger.debug(f"CnOCR: Detection model providers: {det_providers}")

            if hasattr(self.cnocr, 'rec_model') and hasattr(self.cnocr.rec_model, 'session'):
                rec_providers = self.cnocr.rec_model.session.get_providers()
                self.logger.debug(f"CnOCR: Recognition model providers: {rec_providers}")

        except Exception as e:
            self.logger.debug(f"Could not check CnOCR backend: {e}")

    def is_available(self) -> bool:
        """
        Check if CnOCR is available and initialized.

        Returns:
            True if CnOCR is ready to use, False otherwise
        """
        return self.initialized and self.cnocr is not None

    def process_document(self, doc: DocumentFile, file_path: str, ext: str) -> str:
        """
        Process document with CnOCR using multi-threaded batch processing.

        Args:
            doc: Loaded DocumentFile
            file_path: Original file path (for formatting headers)
            ext: File extension (for determining format)

        Returns:
            Processed markdown content
        """
        if not self.is_available():
            raise RuntimeError("CnOCR is not initialized")

        markdown_content = []

        try:
            # Convert all pages to images for batch processing
            page_images = [
                page.numpy() if hasattr(page, 'numpy') else page
                for page in doc
            ]

            # Process in batches using multi-threading
            batch_size = min(self.batch_size, len(page_images))

            for batch_start in range(0, len(page_images), batch_size):
                batch_end = min(batch_start + batch_size, len(page_images))
                batch_images = page_images[batch_start:batch_end]

                # Process this batch with threading
                batch_results = self._process_batch(batch_images, batch_start)

                # Format results as markdown
                for batch_idx, ocr_result in enumerate(batch_results):
                    page_idx = batch_start + batch_idx
                    page_text = self._extract_text_from_result(ocr_result)

                    # Format content based on file type
                    formatted_text = self._format_page_content(page_text, page_idx, file_path, ext)
                    markdown_content.append(formatted_text)

                    self.logger.debug(f"CnOCR processed page {page_idx + 1} with {len(ocr_result) if ocr_result else 0} text blocks")

        except Exception as e:
            self.logger.error(f"CnOCR processing failed: {e}")
            raise

        return "\n\n".join(markdown_content)

    def _process_batch(self, batch_images: list, batch_start: int) -> list:
        """
        Process a batch of images using multi-threading.

        Args:
            batch_images: List of image arrays to process
            batch_start: Starting index for this batch

        Returns:
            List of OCR results for each image in the batch
        """
        # Limit concurrent threads to num_threads
        max_workers = min(self.num_threads, len(batch_images))
        self.logger.debug(f"Processing batch: pages {batch_start + 1}-{batch_start + len(batch_images)} with {max_workers} threads")

        batch_results = [None] * len(batch_images)

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all pages in this batch
                future_to_idx = {
                    executor.submit(self._process_single_page, batch_start + i, img): i
                    for i, img in enumerate(batch_images)
                }

                # Collect results as they complete
                for future in as_completed(future_to_idx):
                    batch_idx = future_to_idx[future]
                    page_idx, ocr_result, error = future.result()
                    batch_results[batch_idx] = ocr_result

                    if error:
                        self.logger.warning(f"Thread for page {page_idx + 1} encountered error: {error}")

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            # Fallback to sequential processing
            for i, img in enumerate(batch_images):
                try:
                    page_idx, ocr_result, _ = self._process_single_page(batch_start + i, img)
                    batch_results[i] = ocr_result
                except Exception as page_error:
                    self.logger.error(f"Failed to process page {batch_start + i + 1}: {page_error}")
                    batch_results[i] = []

        return batch_results

    def _process_single_page(self, page_idx: int, img) -> tuple:
        """
        Process a single page with CnOCR.

        Args:
            page_idx: Page index (for logging)
            img: Image array to process

        Returns:
            Tuple of (page_idx, ocr_result, error)
        """
        try:
            # Pass rec_batch_size to enable batch processing of detected text boxes
            ocr_result = self.cnocr.ocr(img, rec_batch_size=self.batch_size)
            return (page_idx, ocr_result, None)
        except Exception as e:
            self.logger.warning(f"CnOCR recognition failed for page {page_idx + 1}: {e}")
            return (page_idx, [], str(e))

    def _extract_text_from_result(self, ocr_result) -> str:
        """
        Extract text from CnOCR result, handling different result formats.

        Args:
            ocr_result: OCR result from CnOCR

        Returns:
            Extracted text as string
        """
        if not ocr_result or len(ocr_result) == 0:
            return ""

        text_lines = []
        for item in ocr_result:
            if isinstance(item, dict) and 'text' in item:
                # Format: {'text': '...', 'score': 0.9, 'position': [...]}
                text_lines.append(item['text'])
            elif isinstance(item, (list, tuple)) and len(item) > 1:
                # Format: [bbox, text, confidence] or similar
                text_lines.append(str(item[1]))
            elif isinstance(item, str):
                # Direct text
                text_lines.append(item)
            else:
                # Other formats, convert to string
                text_lines.append(str(item))

        return '\n'.join([line.strip() for line in text_lines if line.strip()])

    def _format_page_content(self, page_text: str, page_idx: int, file_path: str, ext: str) -> str:
        """
        Format page content as markdown based on file type.

        Args:
            page_text: Extracted text from page
            page_idx: Page index (0-based)
            file_path: Original file path
            ext: File extension

        Returns:
            Formatted markdown string
        """
        # For single images, use filename as header
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
            return f"# {os.path.basename(file_path)}\n\n{page_text}"

        # For multi-page documents, use page numbers
        return f"## Page {page_idx + 1}\n\n{page_text}"
