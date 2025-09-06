"""
OCR processor implementation using the abstract base class.

This module provides a clean, reusable OCR processor that follows
the FileProcessorBase interface for consistent behavior.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from doctr.io import DocumentFile

from .base import FileProcessorBase, ProcessingResult
from ..converters import get_office_converter
from ..utils import get_temp_manager, get_path_normalizer


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
            from cnocr import CnOcr
            import os
            
            # Clear font path environment variable to avoid issues
            if 'FONTPATH' in os.environ:
                del os.environ['FONTPATH']
            
            # Let CnOCR use default configuration and auto-select backend
            self.cnocr = CnOcr()
            
            # Debug: Check which backend CnOCR is actually using
            try:
                import onnxruntime as ort
                providers = ort.get_available_providers()
                self.logger.info(f"CnOCR: Available providers: {providers}")
                
                # Check if CUDA is being used
                if hasattr(self.cnocr, 'det_model') and hasattr(self.cnocr.det_model, 'session'):
                    det_providers = self.cnocr.det_model.session.get_providers()
                    self.logger.info(f"CnOCR: Detection model providers: {det_providers}")
                
                if hasattr(self.cnocr, 'rec_model') and hasattr(self.cnocr.rec_model, 'session'):
                    rec_providers = self.cnocr.rec_model.session.get_providers()
                    self.logger.info(f"CnOCR: Recognition model providers: {rec_providers}")
                    
            except Exception as e:
                self.logger.debug(f"Could not check CnOCR backend: {e}")
            
            self.logger.info("CnOCR initialized successfully for Chinese text recognition")
        except ImportError as e:
            self.logger.warning("CnOCR not available, falling back to DocTR")
            self.use_cnocr = False
        except Exception as e:
            self.logger.warning(f"Failed to initialize CnOCR: {e}, falling back to DocTR")
            self.use_cnocr = False
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats for OCR processing."""
        return [
            # PDF files
            '.pdf',
            # Image files
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif',
            # Office documents (converted to PDF first)
            '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'
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
            
            self.logger.debug(f"OCR processed {file_path} successfully")
            
        except Exception as e:
            return self._handle_exception(e, result)
        
        finally:
            # Clean up temporary files
            if result.temp_files:
                cleanup_temp_files(result.temp_files)
        
        result.processing_time = time.time() - start_time
        return result
    
    def _load_document(self, file_path: str, ext: str, result: ProcessingResult) -> Optional[DocumentFile]:
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
                self.logger.debug(f"OCR loaded image for processing")
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
            page_images = []
            for page in doc:
                if hasattr(page, 'numpy'):
                    # For PDF pages, convert to numpy array
                    page_img = page.numpy()
                else:
                    # For image files, use the image directly
                    page_img = page
                page_images.append(page_img)
            
            # Process pages in batches using image_list functionality
            batch_size = min(1, len(page_images))  # Process 1 page at a time (single page processing)
            
            for batch_start in range(0, len(page_images), batch_size):
                batch_end = min(batch_start + batch_size, len(page_images))
                batch_images = page_images[batch_start:batch_end]
                
                self.logger.debug(f"Processing batch {batch_start//batch_size + 1}: pages {batch_start + 1}-{batch_end}")
                
                try:
                    # Use CnOCR's image_list functionality for batch processing
                    if hasattr(self.cnocr, 'ocr') and hasattr(self.cnocr.ocr, '__call__'):
                        # Process batch of images
                        batch_results = []
                        for img in batch_images:
                            try:
                                ocr_result = self.cnocr.ocr(img)
                                batch_results.append(ocr_result)
                            except Exception as e:
                                self.logger.warning(f"CnOCR recognition failed for image in batch: {e}")
                                batch_results.append([])
                    else:
                        # Fallback to individual processing
                        batch_results = []
                        for img in batch_images:
                            try:
                                if hasattr(self.cnocr, 'ocr'):
                                    ocr_result = self.cnocr.ocr(img)
                                elif hasattr(self.cnocr, 'readtext'):
                                    ocr_result = self.cnocr.readtext(img)
                                else:
                                    ocr_result = self.cnocr(img)
                                batch_results.append(ocr_result)
                            except Exception as e:
                                self.logger.warning(f"CnOCR recognition failed for image in batch: {e}")
                                batch_results.append([])
                    
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