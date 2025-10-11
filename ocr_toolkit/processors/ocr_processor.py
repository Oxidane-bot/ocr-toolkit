"""
OCR processor implementation using the abstract base class.

This module provides a clean, reusable OCR processor that follows
the FileProcessorBase interface for consistent behavior.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from doctr.io import DocumentFile

from ..converters import get_office_converter
from ..utils import get_path_normalizer, get_temp_manager
from .base import FileProcessorBase, ProcessingResult


def cleanup_temp_files(paths: list[str]) -> None:
    """Safely delete a list of temporary files, ignoring errors."""
    temp_manager = get_temp_manager()
    for path in paths or []:
        temp_manager.cleanup_file(path)


class OCRProcessor(FileProcessorBase):
    """
    OCR processor implementation using DocTR.

    This processor handles OCR processing for PDFs, images, and Office documents
    with proper temporary file management and error handling.
    """

    def __init__(self, ocr_model, batch_size: int = 16, use_cnocr: bool = False):
        """
        Initialize OCR processor.

        Args:
            ocr_model: Loaded DocTR OCR model
            batch_size: Number of pages to process in each batch
            use_cnocr: Whether to use CnOCR for Chinese text recognition (better for Chinese documents)
        """
        super().__init__()
        self.ocr_model = ocr_model
        self.batch_size = batch_size
        self.office_converter = get_office_converter()
        self.use_cnocr = use_cnocr
        self.logger = logging.getLogger(__name__)
        self.temp_manager = get_temp_manager()
        self.path_normalizer = get_path_normalizer()

        # Initialize CnOCR if requested
        if use_cnocr:
            self._initialize_cnocr()

    def _initialize_cnocr(self) -> None:
        """Initialize CnOCR for Chinese text recognition."""
        try:
            import os
            import shutil
            import sys

            from cnocr import CnOcr

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

            # Let CnOCR use default configuration and auto-select backend
            self.cnocr = CnOcr()

            # Debug: Check which backend CnOCR is actually using
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

            self.logger.info("CnOCR initialized successfully for Chinese text recognition")
        except ImportError:
            self.logger.warning("CnOCR not available, falling back to DocTR")
            self.use_cnocr = False
        except FileNotFoundError as e:
            if "huggingface-cli" in str(e):
                self.logger.error("CnOCR model download failed: huggingface-cli not found. "
                                "Please ensure huggingface-hub[cli] is installed.")
            else:
                self.logger.error(f"CnOCR model files missing: {e}")
            self.logger.info("Falling back to DocTR for OCR processing")
            self.use_cnocr = False
        except Exception as e:
            error_msg = str(e)
            if "does not exists" in error_msg or "onnx" in error_msg.lower():
                self.logger.error(f"CnOCR model download incomplete: {e}")
                self.logger.info("You may need to run: huggingface-cli download --help")
                self.logger.info("Or delete CnOCR cache and retry to force model re-download")
            else:
                self.logger.error(f"CnOCR initialization failed: {e}")
            self.logger.info("Falling back to DocTR for OCR processing")
            self.use_cnocr = False

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats for OCR processing."""
        return [
            # PDF files
            '.pdf',
            # Image files
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif',
            # Office documents (converted to PDF first)
            '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            # Text files (direct copy)
            '.txt', '.md', '.rtf'
        ]

    def supports_format(self, file_extension: str) -> bool:
        """Check if this processor supports the given file format."""
        return file_extension.lower() in self.get_supported_formats()

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
            if ext in ['.txt', '.md', '.rtf']:
                content = self._process_text_file(file_path, ext)
                result.content = content
                result.success = True
                result.pages = 1
                self.logger.debug(f"Processed text file {file_path} successfully")
                result.processing_time = time.time() - start_time
                return result

            # Load document based on format
            doc = self._load_document(file_path, ext, result)
            if doc is None:
                result.processing_time = time.time() - start_time
                return result

            # Process with OCR (choose between CnOCR and DocTR)
            # CnOCR can handle both images and PDFs, so use it for all supported formats when requested
            if self.use_cnocr and ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.pdf']:
                content = self._process_with_cnocr(doc, file_path, ext)
            else:
                content = self._process_with_ocr(doc, file_path, ext)

            result.content = content
            result.success = True
            result.pages = len(doc) if doc else 1  # Set the correct page count

            self.logger.debug(f"OCR processed {file_path} successfully with {result.pages} pages")

        except Exception as e:
            return self._handle_exception(e, result)

        finally:
            # Clean up temporary files
            if result.temp_files:
                cleanup_temp_files(result.temp_files)

        result.processing_time = time.time() - start_time
        return result

    def _load_document(self, file_path: str, ext: str, result: ProcessingResult) -> DocumentFile | None:
        """
        Load document file for OCR processing.

        Args:
            file_path: Path to the document
            ext: File extension
            result: Result object to update with temp files

        Returns:
            DocumentFile object or None if loading failed
        """
        try:
            # Handle Chinese path encoding issues on Windows
            normalized_path = self.path_normalizer.normalize_path(file_path)

            if ext == '.pdf':
                # Direct PDF processing
                doc = DocumentFile.from_pdf(normalized_path)
                self.logger.debug(f"OCR loaded PDF with {len(doc)} pages")
                return doc

            elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
                # Direct image processing
                doc = DocumentFile.from_images([normalized_path])
                self.logger.debug("OCR loaded image for processing")
                return doc

            elif ext in ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']:
                # Office document - convert to PDF first
                temp_pdf = self.office_converter.create_temp_pdf(normalized_path)
                if temp_pdf:
                    result.temp_files.append(temp_pdf)
                    doc = DocumentFile.from_pdf(temp_pdf)
                    self.logger.debug(f"OCR converted Office document to PDF with {len(doc)} pages")
                    return doc
                else:
                    result.error = f'Failed to convert Office document {file_path} to PDF'
                    return None

            return None

        except Exception as e:
            result.error = f'Failed to load document for OCR: {str(e)}'
            return None

    def _process_with_ocr(self, doc: DocumentFile, file_path: str, ext: str) -> str:
        """
        Process loaded document with OCR model.

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
            ocr_result = self.ocr_model(batch)

            for page_idx, page_result in enumerate(ocr_result.pages):
                current_page_number = i + page_idx + 1
                text = page_result.render()

                # Format content based on file type
                if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
                    # For single images, use filename as header
                    markdown_content.append(f"# {os.path.basename(file_path)}\n\n{text}")
                else:
                    # For multi-page documents, use page numbers
                    markdown_content.append(f"## Page {current_page_number}\n\n{text}")

        return "\n\n".join(markdown_content)


    def _process_with_cnocr(self, doc: DocumentFile, file_path: str, ext: str) -> str:
        """
        Process loaded document with CnOCR for Chinese text recognition using batch processing.

        Args:
            doc: Loaded DocumentFile
            file_path: Original file path
            ext: File extension

        Returns:
            Processed markdown content
        """
        markdown_content = []

        try:
            # Convert all pages to images for batch processing
            page_images = [
                page.numpy() if hasattr(page, 'numpy') else page
                for page in doc
            ]

            # Multi-threaded processing with optimal thread count for GPU
            # Since CnOCR uses ONNX Runtime which releases GIL, we can use threading
            # Use 4 threads as optimal for GPU to avoid context switching overhead
            NUM_THREADS = 4
            batch_size = min(self.batch_size, len(page_images))

            # Process function for each page
            def process_single_page(page_idx_and_img):
                page_idx, img = page_idx_and_img
                try:
                    # Pass rec_batch_size to enable batch processing of detected text boxes
                    ocr_result = self.cnocr.ocr(img, rec_batch_size=self.batch_size)
                    return (page_idx, ocr_result, None)
                except Exception as e:
                    self.logger.warning(f"CnOCR recognition failed for page {page_idx + 1}: {e}")
                    return (page_idx, [], str(e))

            # Process in batches using ThreadPoolExecutor with limited workers
            for batch_start in range(0, len(page_images), batch_size):
                batch_end = min(batch_start + batch_size, len(page_images))
                batch_images = page_images[batch_start:batch_end]

                # Limit concurrent threads to NUM_THREADS
                max_workers = min(NUM_THREADS, len(batch_images))
                self.logger.debug(f"Processing batch {batch_start//batch_size + 1}: pages {batch_start + 1}-{batch_end} with {max_workers} threads")

                try:
                    # Use threading for parallel processing with limited workers
                    batch_results = [None] * len(batch_images)

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all pages in this batch
                        future_to_idx = {
                            executor.submit(process_single_page, (batch_start + i, img)): i
                            for i, img in enumerate(batch_images)
                        }

                        # Collect results as they complete
                        for future in as_completed(future_to_idx):
                            batch_idx = future_to_idx[future]
                            page_idx, ocr_result, error = future.result()
                            batch_results[batch_idx] = ocr_result

                            if error:
                                self.logger.warning(f"Thread for page {page_idx + 1} encountered error: {error}")

                    # Process batch results
                    for batch_idx, ocr_result in enumerate(batch_results):
                        page_idx = batch_start + batch_idx

                        # Extract text from result
                        if ocr_result and len(ocr_result) > 0:
                            # Handle different result formats from CnOCR
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

                            page_text = '\n'.join([line.strip() for line in text_lines if line.strip()])
                        else:
                            page_text = ""

                        # Format content based on file type
                        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']:
                            # For single images, use filename as header
                            markdown_content.append(f"# {os.path.basename(file_path)}\n\n{page_text}")
                        else:
                            # For multi-page documents, use page numbers
                            markdown_content.append(f"## Page {page_idx + 1}\n\n{page_text}")

                        self.logger.debug(f"CnOCR processed page {page_idx + 1} with {len(ocr_result) if ocr_result else 0} text blocks")

                except Exception as batch_error:
                    self.logger.error(f"Batch processing failed for batch {batch_start//batch_size + 1}: {batch_error}")
                    # Fallback to individual processing for this batch
                    for batch_idx, img in enumerate(batch_images):
                        page_idx = batch_start + batch_idx
                        try:
                            ocr_result = self.cnocr.ocr(img)
                            # Process individual result...
                            # (简化处理，避免重复代码)
                            markdown_content.append(f"## Page {page_idx + 1}\n\n[OCR processing failed]")
                        except Exception as e:
                            markdown_content.append(f"## Page {page_idx + 1}\n\n[OCR processing failed: {e}]")

        except Exception as e:
            self.logger.error(f"CnOCR processing failed: {e}")
            # Fallback to DocTR if CnOCR fails
            return self._process_with_ocr(doc, file_path, ext)

        return "\n\n".join(markdown_content)

    def _process_text_file(self, file_path: str, ext: str) -> str:
        """
        Process text file by reading its content directly.

        Args:
            file_path: Path to the text file
            ext: File extension

        Returns:
            File content as markdown string
        """
        try:
            # Handle Chinese path encoding issues on Windows
            normalized_path = self.path_normalizer.normalize_path(file_path)

            # Read the file content
            with open(normalized_path, encoding='utf-8') as f:
                content = f.read()

            # For markdown files, return content as-is
            if ext == '.md':
                return content

            # For other text files, wrap in markdown format
            filename = os.path.basename(file_path)
            return f"# {filename}\n\n{content}"

        except UnicodeDecodeError:
            # Try different encodings if UTF-8 fails
            try:
                with open(normalized_path, encoding='gbk') as f:
                    content = f.read()
                filename = os.path.basename(file_path)
                if ext == '.md':
                    return content
                return f"# {filename}\n\n{content}"
            except:
                self.logger.error(f"Failed to read text file with UTF-8 or GBK encoding: {file_path}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to read text file {file_path}: {e}")
            raise
