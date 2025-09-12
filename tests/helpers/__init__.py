"""
Test helpers package for OCR toolkit.

Provides utilities, fixtures, and helper functions for testing.
"""

from .test_utils import (
    TestFileManager,
    create_mock_processing_result,
    create_test_directory_structure,
    suppress_logging,
    create_mock_ocr_model,
    get_test_file_path,
    assert_file_exists,
    assert_directory_structure_matches,
    count_files_in_directory,
    MockArgsNamespace
)

__all__ = [
    'TestFileManager',
    'create_mock_processing_result',
    'create_test_directory_structure',
    'suppress_logging',
    'create_mock_ocr_model',
    'get_test_file_path',
    'assert_file_exists',
    'assert_directory_structure_matches',
    'count_files_in_directory',
    'MockArgsNamespace'
]