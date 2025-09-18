"""
File discovery utilities for OCR processing.

This module provides utilities for discovering and validating files
that can be processed by the OCR toolkit.
"""

import os
import logging
from typing import List, Tuple, Set, Optional, Dict
from pathlib import Path

from .. import config


class DirectoryCache:
    """Cache for created directories to avoid redundant os.makedirs calls."""
    
    def __init__(self):
        self._created_dirs = set()
    
    def ensure_directory(self, dir_path: str) -> None:
        """
        Ensure directory exists, using cache to avoid redundant calls.
        
        Args:
            dir_path: Directory path to create
        """
        if dir_path in self._created_dirs:
            return
            
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(dir_path)
            logging.debug(f"Created/verified directory: {dir_path}")
        except (PermissionError, OSError) as e:
            logging.error(f"Failed to create directory {dir_path}: {e}")
            raise
    
    def reset(self) -> None:
        """Reset the cache."""
        self._created_dirs.clear()


# Global instance for directory caching
_directory_cache = DirectoryCache()


def get_directory_cache() -> DirectoryCache:
    """Get the global directory cache instance."""
    return _directory_cache


def _safe_recursive_search(base_path: Path, supported_extensions: Set[str], max_depth: int) -> Tuple[List[str], Dict[str, str]]:
    """
    Safely search for files recursively with depth limit and symlink protection.
    
    Args:
        base_path: Base directory to search from
        supported_extensions: Set of supported file extensions  
        max_depth: Maximum recursion depth
        
    Returns:
        Tuple of (file_list, relative_paths_dict)
    """
    files = []
    file_relative_paths = {}
    visited_paths = set()  # Track visited paths to prevent infinite loops
    
    def _search_recursive(current_path: Path, current_depth: int):
        if current_depth > max_depth:
            logging.warning(f"Maximum depth {max_depth} reached at {current_path}")
            return
            
        # Prevent infinite loops from symlinks
        try:
            real_path = current_path.resolve()
            if real_path in visited_paths:
                logging.debug(f"Skipping already visited path: {current_path}")
                return
            visited_paths.add(real_path)
        except (OSError, RuntimeError) as e:
            logging.warning(f"Cannot resolve path {current_path}: {e}")
            return
            
        try:
            # Get directory contents with error handling
            try:
                dir_items = list(current_path.iterdir())
            except (PermissionError, OSError) as e:
                logging.warning(f"Cannot access directory {current_path}: {e}")
                return
                
            # Sort for consistent ordering
            dir_items.sort(key=lambda p: p.name)
            
            for item in dir_items:
                try:
                    if item.is_file():
                        if item.suffix.lower() in supported_extensions:
                            file_path = str(item)
                            files.append(file_path)
                            # Calculate relative path from base directory
                            rel_path = item.relative_to(base_path)
                            file_relative_paths[file_path] = str(rel_path).replace('\\', '/')
                    elif item.is_dir() and not item.is_symlink():
                        # Recursively search subdirectories (skip symlinks for safety)
                        _search_recursive(item, current_depth + 1)
                except (PermissionError, OSError) as e:
                    logging.warning(f"Cannot access item {item}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Unexpected error processing {current_path}: {e}")
            
    _search_recursive(base_path, 0)
    return files, file_relative_paths


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


def discover_files(input_path: str, recursive: bool = True, max_depth: int = 50) -> Tuple[List[str], str, Dict[str, str]]:
    """
    Discover supported files from a given path (file or directory).

    This function handles both single file and directory inputs, returning
    a list of files that can be processed by the OCR toolkit.

    Args:
        input_path: Path to a file or directory containing supported files
        recursive: Whether to search directories recursively (default: True)
        max_depth: Maximum recursion depth to prevent infinite loops (default: 50)

    Returns:
        Tuple containing:
            - List of supported file paths found
            - Base directory path  
            - Dictionary mapping file paths to their relative paths from base_dir

    Raises:
        FileNotFoundError: If the input path does not exist
        ValueError: If input file is not a supported format
    """
    # Convert to pathlib.Path for better cross-platform handling
    input_path_obj = Path(input_path).resolve()
    
    if not input_path_obj.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files = []
    file_relative_paths = {}
    supported_extensions = get_supported_extensions()

    if input_path_obj.is_dir():
        search_type = "recursively" if recursive else "non-recursively"
        logging.info(f"Input is a directory. Searching {search_type} for supported files in: {input_path}")
        base_dir = str(input_path_obj)
        
        if recursive:
            # Use safe recursive search with depth limit
            try:
                files, file_relative_paths = _safe_recursive_search(
                    input_path_obj, supported_extensions, max_depth
                )
            except Exception as e:
                logging.error(f"Error during recursive search: {e}")
                raise
        else:
            # Original non-recursive behavior using pathlib
            for file_path_obj in sorted(input_path_obj.iterdir()):
                if file_path_obj.is_file():
                    if file_path_obj.suffix.lower() in supported_extensions:
                        file_path = str(file_path_obj)
                        files.append(file_path)
                        file_relative_paths[file_path] = file_path_obj.name
                        
        logging.info(f"Found {len(files)} supported files")
        
    elif input_path_obj.is_file():
        if input_path_obj.suffix.lower() not in supported_extensions:
            raise ValueError(
                f"Input file format '{input_path_obj.suffix}' is not supported. "
                f"Supported formats: {', '.join(sorted(supported_extensions))}"
            )
        base_dir = str(input_path_obj.parent)
        file_path = str(input_path_obj)
        files.append(file_path)
        # For single files, relative path is just the filename
        file_relative_paths[file_path] = input_path_obj.name
    else:
        raise ValueError(f"Input path is neither a file nor a directory: {input_path}")

    if not files:
        logging.info("No supported files found to process")

    # Validate relative paths for safety and reliability
    for file_path, rel_path in file_relative_paths.items():
        # Check for potentially unsafe relative paths
        if '..' in rel_path or os.path.isabs(rel_path):
            logging.warning(f"Potentially unsafe relative path detected: {rel_path} for file {file_path}")
        
        # Check for excessively long paths (Windows has 260 char limit)
        if len(rel_path) > 200:  # Conservative limit to account for output directory path
            logging.warning(f"Relative path may be too long ({len(rel_path)} chars): {rel_path}")
        
        # Check for empty or problematic relative paths
        if not rel_path or rel_path in ['.', '..']:
            logging.warning(f"Empty or problematic relative path: '{rel_path}' for file {file_path}")

    return files, base_dir, file_relative_paths


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


def get_output_file_path(input_path: str, output_dir: Optional[str] = None, preserve_structure: bool = False, relative_path: Optional[str] = None, base_dir: Optional[str] = None) -> str:
    """
    Determine the output file path for a converted Markdown document.
    
    Note: This function NO LONGER creates directories automatically to avoid
    race conditions. The caller is responsible for directory creation.

    Args:
        input_path: The full path to the input document
        output_dir: The directory to save the output file. 
                   If None, a default directory is created based on the mode
        preserve_structure: Whether to preserve the original directory structure
        relative_path: The relative path of the file from the base directory
                      (used when preserve_structure=True)
        base_dir: The base directory for the project (used when preserve_structure=True)

    Returns:
        The full path to the output Markdown file
    """
    # Use pathlib for better path handling
    input_path_obj = Path(input_path)
    output_filename = input_path_obj.stem + '.md'

    if output_dir:
        output_dir_obj = Path(output_dir)
        if preserve_structure and relative_path:
            # Preserve directory structure: use relative path to create subdirectories
            rel_path_obj = Path(relative_path)
            rel_dir = rel_path_obj.parent
            if rel_dir != Path('.'):
                output_path = output_dir_obj / rel_dir / output_filename
            else:
                output_path = output_dir_obj / output_filename
        else:
            # Flat structure: all files in the same output directory
            output_path = output_dir_obj / output_filename
    else:
        # Use the default output directory from config
        if preserve_structure and relative_path and base_dir:
            # For preserve structure mode, use the input base directory
            # This ensures all files with preserved structure go to a unified location
            # within the input directory's root
            base_dir_obj = Path(base_dir)
            default_output_dir = base_dir_obj / config.DEFAULT_MARKDOWN_OUTPUT_DIR
            rel_path_obj = Path(relative_path)
            rel_dir = rel_path_obj.parent
            if rel_dir != Path('.'):
                output_path = default_output_dir / rel_dir / output_filename
            else:
                output_path = default_output_dir / output_filename
        else:
            # Use input file's parent directory for default location (original behavior)
            input_file_dir = input_path_obj.parent
            default_output_dir = input_file_dir / config.DEFAULT_MARKDOWN_OUTPUT_DIR
            output_path = default_output_dir / output_filename
        
    return str(output_path)