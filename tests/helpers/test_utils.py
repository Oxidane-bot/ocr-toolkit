"""
Test utilities and helper functions for OCR toolkit tests.

This module provides common utilities, fixtures, and helper functions
used across different test files to reduce duplication and improve maintainability.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock
import logging


class FileManagerHelper:
    """
    Manages temporary test files and directories for testing.
    
    Provides context manager functionality for creating and cleaning up
    temporary test environments.
    """
    
    def __init__(self):
        self.temp_dirs: List[str] = []
        self.temp_files: List[str] = []
    
    def create_temp_dir(self, prefix: str = "test_") -> str:
        """
        Create a temporary directory.
        
        Args:
            prefix: Prefix for the directory name
            
        Returns:
            Path to the created temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_temp_file(self, content: str = "", suffix: str = ".txt", prefix: str = "test_") -> str:
        """
        Create a temporary file with content.
        
        Args:
            content: Content to write to the file
            suffix: File extension
            prefix: Prefix for the filename
            
        Returns:
            Path to the created temporary file
        """
        fd, temp_file = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            os.close(fd)
            raise
        
        self.temp_files.append(temp_file)
        return temp_file
    
    def cleanup(self) -> None:
        """Clean up all created temporary files and directories."""
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except (OSError, FileNotFoundError):
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except (OSError, FileNotFoundError):
                pass
        
        self.temp_dirs.clear()
        self.temp_files.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_mock_processing_result(success: bool = True, content: str = "Mock content",
                                processing_time: float = 1.0, method: str = "mock",
                                pages: int = 1, file_path: str = "/mock/file.pdf") -> Dict[str, Any]:
    """
    Create a mock processing result for testing.
    
    Args:
        success: Whether the processing was successful
        content: Mock content
        processing_time: Mock processing time
        method: Processing method used
        pages: Number of pages processed
        file_path: Mock file path
        
    Returns:
        Mock processing result dictionary
    """
    return {
        'success': success,
        'content': content,
        'processing_time': processing_time,
        'method': method,
        'pages': pages,
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'error': '' if success else 'Mock error',
        'temp_files': [],
        'metadata': {}
    }


def create_test_directory_structure(base_dir: str, structure: Dict[str, Any]) -> None:
    """
    Create a test directory structure from a nested dictionary.
    
    Args:
        base_dir: Base directory to create structure in
        structure: Nested dictionary representing directory structure
                  Keys are directory/file names, values are either:
                  - Dict: represents a subdirectory
                  - str: represents file content
                  - None: represents empty file
    """
    for name, content in structure.items():
        path = os.path.join(base_dir, name)
        
        if isinstance(content, dict):
            # It's a directory
            os.makedirs(path, exist_ok=True)
            create_test_directory_structure(path, content)
        else:
            # It's a file
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content if content is not None else "")


def suppress_logging(level: int = logging.CRITICAL) -> None:
    """
    Suppress logging output during tests.
    
    Args:
        level: Logging level to set (default: CRITICAL to suppress most output)
    """
    logging.getLogger().setLevel(level)


def create_mock_ocr_model():
    """
    Create a mock OCR model for testing.
    
    Returns:
        Mock OCR model with basic callable interface
    """
    mock_model = Mock()
    mock_model.return_value = Mock()
    mock_model.return_value.pages = [Mock()]
    return mock_model


def get_test_file_path(filename: str) -> str:
    """
    Get the absolute path to a test file.
    
    Args:
        filename: Name of the test file
        
    Returns:
        Absolute path to the test file
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, '..', '..', 'testFile', filename)


def assert_file_exists(file_path: str) -> None:
    """
    Assert that a file exists.
    
    Args:
        file_path: Path to the file to check
        
    Raises:
        AssertionError: If file does not exist
    """
    assert os.path.exists(file_path), f"File does not exist: {file_path}"


def assert_directory_structure_matches(base_dir: str, expected_structure: Dict[str, Any]) -> None:
    """
    Assert that a directory structure matches the expected structure.
    
    Args:
        base_dir: Base directory to check
        expected_structure: Expected directory structure as nested dict
        
    Raises:
        AssertionError: If structure doesn't match
    """
    for name, expected_content in expected_structure.items():
        path = os.path.join(base_dir, name)
        
        if isinstance(expected_content, dict):
            # It's a directory
            assert os.path.isdir(path), f"Expected directory does not exist: {path}"
            assert_directory_structure_matches(path, expected_content)
        else:
            # It's a file
            assert os.path.isfile(path), f"Expected file does not exist: {path}"
            if expected_content is not None:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert content == expected_content, f"File content mismatch in {path}"


def count_files_in_directory(directory: str, extension: Optional[str] = None, recursive: bool = True) -> int:
    """
    Count files in a directory.
    
    Args:
        directory: Directory to count files in
        extension: Optional file extension to filter by (e.g., '.pdf')
        recursive: Whether to count recursively
        
    Returns:
        Number of files found
    """
    count = 0
    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if extension is None or file.endswith(extension):
                    count += 1
    else:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                if extension is None or item.endswith(extension):
                    count += 1
    
    return count


class MockArgsNamespace:
    """
    Mock argparse.Namespace for testing CLI argument handling.
    """
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return f"MockArgsNamespace({', '.join(items)})"