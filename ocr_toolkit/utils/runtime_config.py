"""
OCR runtime environment configuration.

Centralizes logging/warning controls and output suppression used by
third-party OCR/runtime libraries.
"""

import logging
import os
import warnings
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout


def configure_ocr_environment() -> None:
    """
    Configure process-level settings for OCR-related third-party libraries.
    """
    logger_names = [
        "openocr",
        "openocr_unified",
        "infer_doc_onnx",
        "onnxruntime",
    ]
    for name in logger_names:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False


def configure_ocr_warnings() -> None:
    """
    Suppress noisy warnings from OCR runtime internals.
    """
    warnings.filterwarnings("ignore", message=r"(?s)\s*Non compatible API\..*")
    warnings.filterwarnings("ignore", message=r"(?s)\s*To copy construct from a tensor.*")


@contextmanager
def suppress_external_library_output() -> Iterator[None]:
    """
    Suppress third-party stdout/stderr noise during OCR model operations.

    Uses both Python stream redirection and OS-level FD redirection so output
    from native/C++ extensions is also silenced.
    """
    saved_stdout_fd = None
    saved_stderr_fd = None

    with open(os.devnull, "w", encoding="utf-8", errors="ignore") as devnull:
        try:
            try:
                saved_stdout_fd = os.dup(1)
                os.dup2(devnull.fileno(), 1)
            except OSError:
                saved_stdout_fd = None

            try:
                saved_stderr_fd = os.dup(2)
                os.dup2(devnull.fileno(), 2)
            except OSError:
                saved_stderr_fd = None

            with redirect_stdout(devnull), redirect_stderr(devnull):
                yield
        finally:
            if saved_stdout_fd is not None:
                os.dup2(saved_stdout_fd, 1)
                os.close(saved_stdout_fd)

            if saved_stderr_fd is not None:
                os.dup2(saved_stderr_fd, 2)
                os.close(saved_stderr_fd)
