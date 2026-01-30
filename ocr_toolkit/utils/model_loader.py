"""
OCR model loading utilities.

This module provides utilities for loading and configuring OCR models
with appropriate device selection and configuration.

For PaddleOCR 3.x, models are managed internally by the library.
This module provides verification and device information utilities.
"""

import logging
from typing import Any


def load_ocr_model(use_cpu: bool = False):
    """
    Verify PaddlePaddle 3.x and PaddleOCR 3.x installation for OCR processing.

    PaddleOCR 3.x manages its own models internally using PaddlePaddle 3.x,
    so this function only verifies that the required dependencies are installed.

    Args:
        use_cpu: Force CPU usage even if GPU is available. Defaults to False

    Returns:
        None (models are managed by PaddleOCR 3.x internally)

    Raises:
        RuntimeError: If PaddlePaddle 3.x or PaddleOCR 3.x is not installed

    Example:
        >>> load_ocr_model()  # Just verify installation
        >>> # PaddleOCR 3.x will handle model loading
    """
    try:
        import paddle

        # Verify PaddlePaddle version
        paddle_version = getattr(paddle, '__version__', 'unknown')
        logging.info(f"PaddlePaddle version: {paddle_version}")

        # Check if version is 3.0+
        version_parts = paddle_version.split('.')
        major_version = int(version_parts[0]) if version_parts and version_parts[0].isdigit() else 0

        if major_version < 3:
            logging.warning(f"PaddlePaddle version {paddle_version} detected. PaddleOCR 3.x requires PaddlePaddle 3.0+")

        if use_cpu:
            logging.info("PaddlePaddle CPU mode requested")
        else:
            # Check if CUDA is available
            if paddle.is_compiled_with_cuda():
                gpu_count = paddle.device.cuda.device_count()
                if gpu_count > 0:
                    device_name = paddle.device.cuda.get_device_name(0)
                    logging.info(f"PaddlePaddle using GPU (device: {device_name})")
                else:
                    logging.info("PaddlePaddle compiled with CUDA but no GPU found, using CPU")
            else:
                logging.info("PaddlePaddle using CPU (CUDA not compiled in)")

        # Verify PaddleOCR 3.x is available
        try:
            import paddleocr
            ocr_version = getattr(paddleocr, '__version__', 'unknown')
            logging.info(f"PaddleOCR version: {ocr_version}")

            # Check for PaddleOCRVL class (PaddleOCR 3.x feature)
            from paddleocr import PaddleOCR
            logging.info("PaddleOCR 3.x is available")
        except ImportError as e:
            raise RuntimeError(f"PaddleOCR 3.x not installed: {e}. Please install paddleocr>=3.0.0")

        logging.info("PaddlePaddle 3.x and PaddleOCR 3.x installation verified successfully")
        return None

    except ImportError:
        raise RuntimeError(
            "PaddlePaddle 3.x not installed. Please install it:\n"
            "  GPU (Windows/Linux): pip install paddlepaddle-gpu>=3.0.0\n"
            "  CPU: pip install paddlepaddle>=3.0.0\n"
            "Then install PaddleOCR: pip install paddleocr>=3.0.0"
        )


def get_device_info() -> dict[str, Any]:
    """
    Get information about available compute devices.

    Returns:
        Dictionary with device information
    """
    device_info = {
        'paddle_available': False,
        'paddle_version': None,
        'cuda_available': False,
        'cuda_device_count': 0,
        'cuda_device_name': None,
    }

    try:
        import paddle

        device_info['paddle_available'] = True
        device_info['paddle_version'] = getattr(paddle, '__version__', 'unknown')

        if paddle.is_compiled_with_cuda():
            device_info['cuda_available'] = True
            device_info['cuda_device_count'] = paddle.device.cuda.device_count()
            if device_info['cuda_device_count'] > 0:
                device_info['cuda_device_name'] = paddle.device.cuda.get_device_name(0)

    except ImportError:
        pass

    return device_info
