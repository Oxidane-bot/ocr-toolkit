"""
PaddlePaddle/PaddleOCR environment configuration.

Centralizes environment variables needed to suppress noisy output
from PaddlePaddle and related libraries.
"""

import os
import logging

# Environment variables to suppress noisy PaddlePaddle output
PADDLE_ENV_VARS = {
    'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK': 'True',
    'PADDLE_SDK_CHECK_CONNECTIVITY': 'False',
    'GLOG_MINLOGLEVEL': '3',  # Only show FATAL errors
    'GLOG_V': '0',  # Set verbosity to 0
    'FLAGS_logtostderr': '0',  # Don't log to stderr
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
    logging.getLogger('paddlex').setLevel(logging.ERROR)
    logging.getLogger('paddle').setLevel(logging.ERROR)
    logging.getLogger('Paddle').setLevel(logging.ERROR)
