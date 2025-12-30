"""
Office document to PDF conversion strategy using LibreOffice (soffice).

This strategy is intended to be the primary Office conversion method on Linux,
where Windows COM automation and docx2pdf are unavailable.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import ConversionStrategy


class LibreOfficeStrategy(ConversionStrategy):
    """
    Strategy for converting Office documents via LibreOffice in headless mode.

    Requires the `soffice` binary (LibreOffice) to be installed and available in PATH.
    """

    SUPPORTED_FORMATS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}

    def __init__(self, timeout_seconds: int = 180):
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(__name__)

    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        result = {
            "method": self.get_method_name(),
            "success": False,
            "processing_time": 0,
            "error": "",
        }

        start_time = time.time()

        input_abs = str(Path(input_path).resolve())
        output_abs = str(Path(output_path).resolve())

        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            result["error"] = "LibreOffice not found (missing 'soffice' in PATH)"
            result["processing_time"] = time.time() - start_time
            return result

        out_dir = Path(tempfile.mkdtemp(prefix="ocr_lo_out_")).resolve()
        try:
            cmd = [
                soffice,
                "--headless",
                "--nologo",
                "--nolockcheck",
                "--nodefault",
                "--nofirststartwizard",
                "--norestore",
                "--invisible",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                input_abs,
            ]

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )

            expected = out_dir / f"{Path(input_abs).stem}.pdf"
            produced_pdf: Path | None = expected if expected.exists() else None
            if produced_pdf is None:
                candidates = sorted(out_dir.glob("*.pdf"))
                if candidates:
                    produced_pdf = candidates[0]

            if proc.returncode != 0 or produced_pdf is None or not produced_pdf.exists():
                output = (proc.stdout or "").strip()
                tail = output[-2000:] if output else ""
                result["error"] = (
                    f"LibreOffice conversion failed (code={proc.returncode})."
                    + (f" Output: {tail}" if tail else "")
                )
                result["processing_time"] = time.time() - start_time
                return result

            Path(os.path.dirname(output_abs) or ".").mkdir(parents=True, exist_ok=True)
            shutil.move(str(produced_pdf), output_abs)

            result["success"] = True
            result["processing_time"] = time.time() - start_time
            return result

        except subprocess.TimeoutExpired:
            result["error"] = f"LibreOffice conversion timed out after {self.timeout_seconds}s"
            result["processing_time"] = time.time() - start_time
            return result
        except Exception as e:
            result["error"] = str(e)
            result["processing_time"] = time.time() - start_time
            return result
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def get_method_name(self) -> str:
        return "libreoffice"
