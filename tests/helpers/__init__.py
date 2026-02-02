"""
Test helpers package for OCR toolkit.

Provides utilities, fixtures, and helper functions for testing.
"""

from .test_utils import (
    FileManagerHelper,
    MockArgsNamespace,
    assert_directory_structure_matches,
    assert_file_exists,
    count_files_in_directory,
    create_mock_ocr_model,
    create_mock_processing_result,
    create_test_directory_structure,
    get_test_file_path,
    suppress_logging,
)

__all__ = [
    "FileManagerHelper",
    "create_mock_processing_result",
    "create_test_directory_structure",
    "suppress_logging",
    "create_mock_ocr_model",
    "get_test_file_path",
    "assert_file_exists",
    "assert_directory_structure_matches",
    "count_files_in_directory",
    "MockArgsNamespace",
]
