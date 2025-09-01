"""
Configuration module for OCR toolkit.

This module contains default configuration values used across the OCR toolkit,
including model architectures, processing parameters, output directories, and supported file formats.
"""

from typing import Set

# Default OCR model architectures
DEFAULT_DET_ARCH = "linknet_resnet18"
"""str: Default detection model architecture.

Updated to linknet_resnet18 based on quality comparison testing results.
This model provides the best text recognition accuracy for document processing.
Alternative options include 'fast_tiny', 'db_resnet50', 'db_mobilenet_v3_large', etc.
"""

DEFAULT_RECO_ARCH = "crnn_vgg16_bn"
"""str: Default recognition model architecture.

Updated to crnn_vgg16_bn based on quality comparison testing results.
This model provides superior text recognition accuracy with acceptable performance.
Alternative options include 'crnn_mobilenet_v3_small', 'master', 'sar_resnet31', etc.
"""

# Default processing parameters
DEFAULT_BATCH_SIZE = 16
"""int: Default batch size for processing pages.

This value determines how many pages are processed simultaneously.
Larger values may improve throughput but require more memory.
"""

DEFAULT_WORKERS = 4
"""int: Default number of concurrent workers for batch processing."""

# Default output subdirectory names
DEFAULT_MARKDOWN_OUTPUT_DIR = "markdown_output"
"""str: Default subdirectory name for markdown output files."""

DEFAULT_OCR_OUTPUT_DIR = "output_ocr"
"""str: Default subdirectory name for OCR-processed PDF files."""

# Supported file formats (centralized)
SUPPORTED_PDF_FORMATS = {'.pdf'}
"""Set[str]: PDF file formats supported by the toolkit."""

SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
"""Set[str]: Image file formats supported by OCR processing."""

SUPPORTED_OFFICE_FORMATS = {'.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'}
"""Set[str]: Office document formats that can be converted to PDF for OCR."""

SUPPORTED_TEXT_FORMATS = {'.txt', '.md', '.html', '.htm', '.rtf'}
"""Set[str]: Text document formats supported by MarkItDown."""

SUPPORTED_OPENDOC_FORMATS = {'.odt', '.odp', '.ods'}
"""Set[str]: OpenDocument formats supported by MarkItDown."""

SUPPORTED_DATA_FORMATS = {'.csv', '.tsv', '.json', '.xml'}
"""Set[str]: Data file formats supported by MarkItDown."""

SUPPORTED_EBOOK_FORMATS = {'.epub'}
"""Set[str]: E-book formats supported by MarkItDown."""


def get_all_supported_formats() -> Set[str]:
    """
    Get the complete set of all supported file formats.
    
    Returns:
        Set of all supported file extensions
    """
    return (SUPPORTED_PDF_FORMATS | 
            SUPPORTED_IMAGE_FORMATS | 
            SUPPORTED_OFFICE_FORMATS | 
            SUPPORTED_TEXT_FORMATS |
            SUPPORTED_OPENDOC_FORMATS |
            SUPPORTED_DATA_FORMATS |
            SUPPORTED_EBOOK_FORMATS)


def get_ocr_supported_formats() -> Set[str]:
    """
    Get file formats that can be processed by OCR.
    
    Returns:
        Set of OCR-supported file extensions
    """
    return SUPPORTED_PDF_FORMATS | SUPPORTED_IMAGE_FORMATS | SUPPORTED_OFFICE_FORMATS


def get_markitdown_supported_formats() -> Set[str]:
    """
    Get file formats that can be processed by MarkItDown.
    
    Returns:
        Set of MarkItDown-supported file extensions
    """
    return (SUPPORTED_PDF_FORMATS | 
            SUPPORTED_OFFICE_FORMATS | 
            SUPPORTED_TEXT_FORMATS |
            SUPPORTED_OPENDOC_FORMATS |
            SUPPORTED_DATA_FORMATS |
            SUPPORTED_EBOOK_FORMATS)
