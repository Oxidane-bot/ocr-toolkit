"""
File discovery utilities for OCR processing.

This module provides utilities for discovering and validating files
that can be processed by the OCR toolkit.
"""

import os
import logging
from typing import List, Tuple, Set, Optional
from pathlib import Path

from .. import config


def get_supported_extensions() -> Set[str]:
    """
    Get the complete set of supported file extensions.
    
    Returns:
        Set of supported file extensions including the dot
    """
    return config.get_all_supported_formats()


def is_supported_file(file_path: str) -> bool:
    """
    Check if a file is supported for processing.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if the file format is supported, False otherwise
    """
    ext = Path(file_path).suffix.lower()
    return ext in get_supported_extensions()


def discover_files(input_path: str) -> Tuple[List[str], str]:
    """
    Discover supported files from a given path (file or directory).

    This function handles both single file and directory inputs, returning
    a list of files that can be processed by the OCR toolkit.

    Args:
        input_path: Path to a file or directory containing supported files

    Returns:
        Tuple containing:
            - List of supported file paths found
            - Base directory path

    Raises:
        FileNotFoundError: If the input path does not exist
        ValueError: If input file is not a supported format
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files = []
    base_dir = ""
    supported_extensions = get_supported_extensions()

    if os.path.isdir(input_path):
        logging.info(f"Input is a directory. Searching for supported files in: {input_path}")
        base_dir = input_path
        
        for filename in sorted(os.listdir(input_path)):
            file_path = os.path.join(input_path, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in supported_extensions:
                    files.append(file_path)
                    
        logging.info(f"Found {len(files)} supported files")
        
    elif os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in supported_extensions:
            raise ValueError(
                f"Input file format '{ext}' is not supported. "
                f"Supported formats: {', '.join(sorted(supported_extensions))}"
            )
        base_dir = os.path.dirname(input_path)
        files.append(input_path)
    else:
        raise ValueError(f"Input path is neither a file nor a directory: {input_path}")

    if not files:
        logging.info("No supported files found to process")

    return files, base_dir


def discover_pdf_files(input_path: str) -> Tuple[List[str], str]:
    """
    Discover PDF files from a given path (file or directory).
    
    This function is specialized for PDF-only processing.
    
    Args:
        input_path: Path to a file or directory containing PDF files
        
    Returns:
        Tuple containing:
            - List of PDF file paths found
            - Base directory path
            
    Raises:
        FileNotFoundError: If the input path does not exist
        ValueError: If input file is not a PDF
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files = []
    base_dir = ""
    
    if os.path.isdir(input_path):
        logging.info(f"Input is a directory. Searching for PDF files in: {input_path}")
        base_dir = input_path
        
        for filename in sorted(os.listdir(input_path)):
            file_path = os.path.join(input_path, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext == '.pdf':
                    files.append(file_path)
                    
        logging.info(f"Found {len(files)} PDF files")
        
    elif os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext != '.pdf':
            raise ValueError(f"Input file format '{ext}' is not supported. Only PDF files are supported.")
        base_dir = os.path.dirname(input_path)
        files.append(input_path)
    else:
        raise ValueError(f"Input path is neither a file nor a directory: {input_path}")

    if not files:
        logging.info("No PDF files found to process")

    return files, base_dir


def get_output_file_path(input_path: str, output_dir: Optional[str] = None) -> str:
    """
    Determine the output file path for a converted Markdown document.

    Args:
        input_path: The full path to the input document
        output_dir: The directory to save the output file. 
                   If None, a default directory is created in the input file's directory

    Returns:
        The full path to the output Markdown file
    """
    input_filename = os.path.basename(input_path)
    output_filename = os.path.splitext(input_filename)[0] + '.md'

    if output_dir:
        output_path = os.path.join(output_dir, output_filename)
    else:
        # Use the default output directory from config
        input_file_dir = os.path.dirname(input_path)
        default_output_dir = os.path.join(input_file_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        output_path = os.path.join(default_output_dir, output_filename)
        
    return output_path