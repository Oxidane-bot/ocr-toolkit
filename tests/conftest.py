"""
Pytest configuration and fixtures for OCR toolkit tests.
"""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test file paths - using the existing testFile directory
TEST_FILES_DIR = project_root / "testFile"

# Individual test files
TEST_FILES = {
    'pdf1': TEST_FILES_DIR / "instructions for writing 4-1.pdf",
    'pdf2': TEST_FILES_DIR / "lesson4.pdf", 
    'image1': TEST_FILES_DIR / "choice question.jpg",
    'image2': TEST_FILES_DIR / "discussion 4 instructions.jpg"
}


@pytest.fixture
def test_files():
    """Provide access to real test files."""
    # Verify test files exist
    missing_files = [name for name, path in TEST_FILES.items() if not path.exists()]
    if missing_files:
        pytest.skip(f"Test files missing: {missing_files}")
    
    return TEST_FILES


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    file_path = os.path.join(temp_dir, "sample.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("This is sample text for testing.")
    return file_path


@pytest.fixture
def sample_markdown():
    """Sample markdown content for testing."""
    return """# Test Document

This is a test document with proper formatting.

## Section 1

- First bullet point
- Second bullet point

## Section 2

1. First numbered item
2. Second numbered item

This document has good structure."""


@pytest.fixture
def mock_ocr_result():
    """Mock OCR processing result for testing."""
    return {
        'success': True,
        'content': 'OCR extracted text content',
        'processing_time': 1.5,
        'method': 'ocr',
        'error': ''
    }