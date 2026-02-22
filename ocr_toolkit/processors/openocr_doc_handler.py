"""
OpenOCR OpenDoc handler.

Provides document parsing with OpenOCR/OpenDoc-0.1B.
"""

import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from ..utils.model_loader import setup_nvidia_dll_paths
from ..utils.profiling import Profiler
from ..utils.runtime_config import (
    configure_ocr_environment,
    configure_ocr_warnings,
    suppress_external_library_output,
)

# Keep global env/warning guards to suppress third-party noise in CLI mode.
configure_ocr_environment()
configure_ocr_warnings()


class OpenOCRDocHandler:
    """
    Handler for OpenOCR OpenDoc-0.1B document parsing.
    """

    def __init__(
        self,
        use_gpu: bool = True,
        model_name: str = "OpenDoc-0.1B",
        with_images: bool = False,
        auto_download: bool = True,
        use_layout_detection: bool = True,
        layout_threshold: float = 0.4,
        max_length: int = 2048,
        max_parallel_blocks: int = 4,
    ):
        self.use_gpu = use_gpu
        self.model_name = model_name
        self.with_images = with_images
        self.auto_download = auto_download
        self.use_layout_detection = use_layout_detection
        self.layout_threshold = layout_threshold
        self.max_length = max_length
        self.max_parallel_blocks = max_parallel_blocks
        self.logger = logging.getLogger(__name__)
        self.pipeline = None
        self.initialized = False
        self._output_dir: str | None = None

        self._initialize()

    def _initialize(self) -> bool:
        """
        Initialize OpenOCR doc pipeline.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        try:
            self.logger.info(f"Initializing OpenOCR doc pipeline with model: {self.model_name}")
            setup_nvidia_dll_paths()

            from openocr import OpenOCR
            configure_ocr_environment()

            if self.use_gpu:
                try:
                    with suppress_external_library_output():
                        self.pipeline = OpenOCR(
                            task="doc",
                            use_gpu="true",
                            auto_download=self.auto_download,
                            use_layout_detection=self.use_layout_detection,
                            layout_threshold=self.layout_threshold,
                            max_parallel_blocks=self.max_parallel_blocks,
                        )
                    self.logger.info("Using CUDA for OpenOCR OpenDoc inference")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize CUDA inference: {e}. Falling back to CPU.")
                    with suppress_external_library_output():
                        self.pipeline = OpenOCR(
                            task="doc",
                            use_gpu="false",
                            auto_download=self.auto_download,
                            use_layout_detection=self.use_layout_detection,
                            layout_threshold=self.layout_threshold,
                            max_parallel_blocks=self.max_parallel_blocks,
                        )
                    self.use_gpu = False
                    self.logger.info("Using CPU for OpenOCR OpenDoc inference")
            else:
                with suppress_external_library_output():
                    self.pipeline = OpenOCR(
                        task="doc",
                        use_gpu="false",
                        auto_download=self.auto_download,
                        use_layout_detection=self.use_layout_detection,
                        layout_threshold=self.layout_threshold,
                        max_parallel_blocks=self.max_parallel_blocks,
                    )
                self.logger.info("Using CPU for OpenOCR OpenDoc inference")

            self.initialized = True
            self.logger.info("OpenOCR OpenDoc initialized successfully")
            return True
        except ImportError:
            self.logger.error("OpenOCR not available. Install with: pip install openocr-python")
            self.initialized = False
            return False
        except Exception as e:
            self.logger.error(f"OpenOCR initialization failed: {e}")
            self.initialized = False
            return False

    def is_available(self) -> bool:
        return self.initialized and self.pipeline is not None

    def process_document(
        self,
        file_path: str,
        *,
        output_dir: str | None = None,
        pages: str | None = None,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Process document with OpenOCR.

        Args:
            file_path: Path to the document (PDF or image).
            output_dir: Directory to save extracted images.
            pages: Optional page selection (e.g., "1-3,5,7-9").
            profiler: Optional profiler for performance tracking.
        """
        if not self.is_available():
            raise RuntimeError("OpenOCR doc pipeline is not initialized")

        self._output_dir = output_dir
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf" and pages:
            return self._process_pdf_with_page_selection(file_path, pages, profiler)

        return self._process_single_document(file_path, profiler)

    def _predict_safely(self, file_path: str):
        with suppress_external_library_output():
            return self.pipeline(
                image_path=file_path,
                layout_threshold=self.layout_threshold,
                max_length=self.max_length,
            )

    def _process_single_document(
        self,
        file_path: str,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if profiler:
            with profiler.track("openocr_doc_predict"):
                output = self._predict_safely(file_path)
        else:
            output = self._predict_safely(file_path)

        return self._extract_output(output, file_path)

    def _process_pdf_with_page_selection(
        self,
        pdf_path: str,
        pages: str,
        profiler: Profiler | None = None,
    ) -> tuple[str, dict[str, Any]]:
        import pypdfium2 as pdfium

        from ..utils.page_selection import parse_pages_arg

        parsed_pages = parse_pages_arg(pages)

        pdf = pdfium.PdfDocument(pdf_path)
        try:
            total_pages = len(pdf)
            requested = parsed_pages.indices
            page_indices = [i for i in requested if 0 <= i < total_pages]
            if not page_indices:
                raise ValueError(f"No valid pages selected (total pages: {total_pages})")
        finally:
            pdf.close()

        self.logger.info(f"Processing {len(page_indices)} selected PDF pages with OpenOCR")

        markdown_pages: list[str] = []
        metadata: dict[str, Any] = {
            "total_pages": total_pages,
            "selected_pages": page_indices,
            "page_count": len(page_indices),
            "engine": "openocr_doc",
            "model": self.model_name,
        }

        for page_idx in page_indices:
            temp_image = self._extract_page_to_image(pdf_path, page_idx)
            try:
                if profiler:
                    with profiler.track("openocr_doc_predict_page"):
                        page_output = self._predict_safely(temp_image)
                else:
                    page_output = self._predict_safely(temp_image)

                page_md, _ = self._extract_output(page_output, pdf_path)
                page_number = page_idx + 1
                markdown_pages.append(f"## Page {page_number}\n\n{page_md}".strip())
            finally:
                if os.path.exists(temp_image):
                    os.remove(temp_image)

        return "\n\n".join(markdown_pages), metadata

    def _extract_page_to_image(self, pdf_path: str, page_idx: int) -> str:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(pdf_path)
        try:
            page = pdf[page_idx]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            pil_image.save(temp_path)
            return temp_path
        finally:
            pdf.close()

    def _extract_output(self, output: Any, file_path: str) -> tuple[str, dict[str, Any]]:
        metadata: dict[str, Any] = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "engine": "openocr_doc",
            "model": self.model_name,
        }

        markdown_parts: list[str] = []
        image_metadata_list: list[dict[str, Any]] = []
        page_count = 0

        if isinstance(output, list):
            for result in output:
                content, image_metadata = self._extract_single_result(result)
                if content.strip():
                    markdown_parts.append(content.strip())
                if image_metadata:
                    image_metadata_list.append(image_metadata)
                page_count += 1
        else:
            content, image_metadata = self._extract_single_result(output)
            if content.strip():
                markdown_parts.append(content.strip())
            if image_metadata:
                image_metadata_list.append(image_metadata)
            page_count = 1

        metadata["page_count"] = page_count
        if image_metadata_list:
            metadata["image_metadata"] = image_metadata_list
            metadata["total_extracted_images"] = sum(
                int(item.get("extracted_images", 0)) for item in image_metadata_list
            )

        return "\n\n".join(markdown_parts), metadata

    def _extract_single_result(self, result: Any) -> tuple[str, dict[str, Any] | None]:
        if isinstance(result, dict) and hasattr(self.pipeline, "save_to_markdown"):
            temp_dir = tempfile.mkdtemp(prefix="openocr_md_")
            try:
                self.pipeline.save_to_markdown(result, temp_dir)
                markdown_file = self._find_first_markdown_file(temp_dir)
                if markdown_file is not None:
                    content = markdown_file.read_text(encoding="utf-8")
                    return self._handle_images(markdown_file, content)
            except Exception as e:
                self.logger.debug(f"Could not extract markdown via save_to_markdown: {e}")
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

        if isinstance(result, dict):
            return self._extract_text_from_result(result), None

        return str(result), None

    def _find_first_markdown_file(self, root_dir: str) -> Path | None:
        files = sorted(Path(root_dir).rglob("*.md"))
        return files[0] if files else None

    def _handle_images(
        self,
        markdown_file: Path,
        content: str,
    ) -> tuple[str, dict[str, Any] | None]:
        imgs_dir = markdown_file.parent / "imgs"
        image_metadata: dict[str, Any] | None = None

        if self.with_images and self._output_dir and imgs_dir.exists():
            timestamp = str(int(time.time() * 1000))
            images_dir_name = f"imgs_{timestamp}"
            output_imgs_dir = Path(self._output_dir) / images_dir_name
            output_imgs_dir.mkdir(parents=True, exist_ok=True)

            copied_count = 0
            for image_path in imgs_dir.rglob("*"):
                if image_path.is_file():
                    relative = image_path.relative_to(imgs_dir)
                    target_path = output_imgs_dir / relative
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(image_path, target_path)
                    copied_count += 1

            if copied_count > 0:
                content = content.replace("](imgs/", f"]({images_dir_name}/")
                content = content.replace('src="imgs/', f'src="{images_dir_name}/')
                content = content.replace("src='imgs/", f"src='{images_dir_name}/")
                image_metadata = {
                    "extracted_images": copied_count,
                    "images_dir": images_dir_name,
                }
        else:
            content = re.sub(r"!\[.*?\]\([^)]+\)", "", content)
            content = re.sub(r"<img[^>]*>", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()

        return content, image_metadata

    def _extract_text_from_result(self, result: dict[str, Any]) -> str:
        recognition_results = result.get("recognition_results")
        if isinstance(recognition_results, list):
            parts: list[str] = []
            for item in recognition_results:
                if not isinstance(item, dict):
                    continue
                text = (item.get("text") or item.get("text_unirec") or "").strip()
                if text:
                    parts.append(text)
            if parts:
                return "\n\n".join(parts)

        markdown_text = result.get("markdown")
        if isinstance(markdown_text, str):
            return markdown_text

        text_value = result.get("text")
        if isinstance(text_value, str):
            return text_value

        return str(result)

    def set_output_dir(self, output_dir: str):
        self._output_dir = output_dir
