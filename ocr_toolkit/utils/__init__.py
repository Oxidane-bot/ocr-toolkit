"""
Utility modules for OCR toolkit.

This package provides various utility functions and classes that support
the main OCR processing functionality.
"""

from .file_discovery import discover_files, discover_pdf_files, get_output_file_path, is_supported_file, get_supported_extensions, get_directory_cache
from .file_tree_display import generate_file_tree
from .model_loader import load_ocr_model, get_device_info
from .cli_args import add_common_ocr_args, add_output_args
from .temp_file_manager import TempFileManager, get_temp_manager, cleanup_temp_files
from .path_normalizer import PathNormalizer, get_path_normalizer, normalize_file_path
from .cli_common import setup_logging, BaseArgumentParser, validate_common_arguments, configure_logging_level, check_input_path_exists, print_processing_summary

__all__ = [
    'discover_files', 'discover_pdf_files', 'get_output_file_path', 'is_supported_file', 'get_supported_extensions', 'get_directory_cache', 'generate_file_tree',
    'load_ocr_model', 'get_device_info',
    'add_common_ocr_args', 'add_output_args',
    'TempFileManager', 'get_temp_manager', 'cleanup_temp_files',
    'PathNormalizer', 'get_path_normalizer', 'normalize_file_path',
    'setup_logging', 'BaseArgumentParser', 'validate_common_arguments', 'configure_logging_level', 'check_input_path_exists', 'print_processing_summary'
]