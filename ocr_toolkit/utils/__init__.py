"""
Utility modules for OCR toolkit.

This package provides various utility functions and classes that support
the main OCR processing functionality.
"""

from .cli_args import add_common_ocr_args, add_output_args
from .cli_common import (
    BaseArgumentParser,
    check_input_path_exists,
    configure_logging_level,
    print_processing_summary,
    setup_logging,
    setup_logging_with_file,
    validate_common_arguments,
)
from .file_discovery import (
    discover_files,
    discover_pdf_files,
    get_directory_cache,
    get_output_file_path,
    get_supported_extensions,
    is_supported_file,
)
from .file_tree_display import generate_file_tree
from .path_normalizer import PathNormalizer, get_path_normalizer, normalize_file_path
from .temp_file_manager import TempFileManager, cleanup_temp_files, get_temp_manager
from .paddle_config import configure_paddle_environment

def load_ocr_model(*args, **kwargs):
    from .model_loader import load_ocr_model as _load_ocr_model
    return _load_ocr_model(*args, **kwargs)


def get_device_info():
    from .model_loader import get_device_info as _get_device_info
    return _get_device_info()

__all__ = [
    'discover_files', 'discover_pdf_files', 'get_output_file_path', 'is_supported_file', 'get_supported_extensions', 'get_directory_cache', 'generate_file_tree',
    'load_ocr_model', 'get_device_info',
    'add_common_ocr_args', 'add_output_args',
    'TempFileManager', 'get_temp_manager', 'cleanup_temp_files',
    'PathNormalizer', 'get_path_normalizer', 'normalize_file_path',
    'setup_logging', 'setup_logging_with_file', 'BaseArgumentParser', 'validate_common_arguments', 'configure_logging_level', 'check_input_path_exists', 'print_processing_summary',
    'configure_paddle_environment'
]
