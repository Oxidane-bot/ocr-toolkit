"""
OCR model loading utilities.

This module provides utilities for loading and configuring OCR models
with appropriate device selection and configuration.
"""

import logging
from typing import Any

import torch
from doctr.models import ocr_predictor

from .. import config


def load_ocr_model(det_arch: str = None, reco_arch: str = None, use_cpu: bool = False):
    """
    Load and return a doctr OCR predictor model.

    This function creates an OCR predictor with the specified architectures
    and configures it for GPU or CPU usage based on availability and user preference.

    Args:
        det_arch: Detection model architecture name. If None, uses default from config
        reco_arch: Recognition model architecture name. If None, uses default from config
        use_cpu: Force CPU usage even if CUDA is available. Defaults to False

    Returns:
        doctr.models.OCRPredictor: The loaded OCR predictor model

    Example:
        >>> model = load_ocr_model('fast_tiny', 'crnn_mobilenet_v3_small')
        >>> # Process documents with the loaded model
    """
    # Use defaults from config if not specified
    det_arch = det_arch or config.DEFAULT_DET_ARCH
    reco_arch = reco_arch or config.DEFAULT_RECO_ARCH

    logging.info(f"Loading model with det_arch='{det_arch}' and reco_arch='{reco_arch}'...")

    use_gpu = not use_cpu and torch.cuda.is_available()

    if use_gpu:
        device_name = None
        try:
            device_name = torch.cuda.get_device_name(0)
        except Exception:
            device_name = None

        suffix = f" (device: {device_name})" if device_name else ""
        logging.info(f"CUDA is available. Using GPU for doctr{suffix}")
        model = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True).cuda()
    else:
        logging.info("Using CPU for doctr")
        model = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True)

    try:
        model.eval()
    except Exception:
        pass

    logging.info("Model loaded successfully")
    return model


def get_device_info() -> dict[str, Any]:
    """
    Get information about available compute devices.

    Returns:
        Dictionary with device information
    """
    return {
        'cuda_available': torch.cuda.is_available(),
        'cuda_device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        'cuda_device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    }
