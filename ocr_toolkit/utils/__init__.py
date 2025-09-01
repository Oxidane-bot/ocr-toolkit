"""
Utility modules for OCR toolkit.

This package provides various utility functions and classes that support
the main OCR processing functionality.
"""

from .file_discovery import discover_files, get_output_file_path, is_supported_file, get_supported_extensions
from .model_loader import load_ocr_model, get_device_info
from .cli_args import add_common_ocr_args, add_output_args

__all__ = [
    'discover_files', 'get_output_file_path', 'is_supported_file', 'get_supported_extensions',
    'load_ocr_model', 'get_device_info',
    'add_common_ocr_args', 'add_output_args'
]