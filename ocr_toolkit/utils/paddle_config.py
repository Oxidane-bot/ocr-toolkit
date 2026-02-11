"""
PaddlePaddle/PaddleOCR environment configuration.

Centralizes environment variables needed to suppress noisy output
from PaddlePaddle and related libraries.
"""

from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import logging
import os
import warnings

# Environment variables to suppress noisy PaddlePaddle output
PADDLE_ENV_VARS = {
    "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
    "PADDLE_SDK_CHECK_CONNECTIVITY": "False",
    "GLOG_MINLOGLEVEL": "3",  # Only show FATAL errors
    "GLOG_V": "0",  # Set verbosity to 0
    "FLAGS_logtostderr": "0",  # Don't log to stderr
}


def configure_paddle_environment() -> None:
    """
    Configure environment variables for PaddlePaddle/PaddleOCR.

    This should be called before importing any PaddlePaddle modules
    to suppress their noisy logging output.
    """
    for key, value in PADDLE_ENV_VARS.items():
        os.environ[key] = value

    # Also suppress logging at Python level
    logging.getLogger("paddlex").setLevel(logging.ERROR)
    logging.getLogger("paddle").setLevel(logging.ERROR)
    logging.getLogger("Paddle").setLevel(logging.ERROR)


def configure_paddle_warnings() -> None:
    """
    Suppress noisy warnings emitted by Paddle/PaddleOCR internals.

    These warnings are informational for framework compatibility and do not
    represent actionable issues for this application.
    """
    warnings.filterwarnings("ignore", message=r"(?s)\s*Non compatible API\..*")
    warnings.filterwarnings("ignore", message=r"(?s)\s*To copy construct from a tensor.*")


@contextmanager
def suppress_external_library_output() -> Iterator[None]:
    """
    Suppress third-party stdout/stderr noise during Paddle model operations.

    Uses both Python stream redirection and OS-level FD redirection so output
    from native/C++ extensions is also silenced.
    """
    saved_stdout_fd = None
    saved_stderr_fd = None

    with open(os.devnull, "w") as devnull:
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
