"""
Path normalization service for handling file paths across different platforms.

This module provides utilities for normalizing file paths to handle
character encoding issues, especially with Chinese characters on Windows.
"""

import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from ..utils.temp_file_manager import get_temp_manager


class PathNormalizer:
    """
    Service for normalizing file paths to handle encoding and compatibility issues.
    
    This class provides utilities for handling file paths that may contain
    non-ASCII characters, particularly on Windows systems.
    """
    
    def __init__(self):
        """Initialize the path normalizer."""
        self.logger = logging.getLogger(__name__)
        self.temp_manager = get_temp_manager()
    
    def normalize_path(self, file_path: str) -> str:
        """
        Normalize file path to handle encoding issues and special characters.
        
        Args:
            file_path: Original file path
            
        Returns:
            Normalized file path that can be safely used with libraries
        """
        if not file_path:
            return file_path
            
        try:
            # Convert to Path object for better handling
            path_obj = Path(file_path)
            
            # Check if file exists
            if not path_obj.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return file_path
            
            # On Windows, check if path contains non-ASCII characters
            if os.name == 'nt':  # Windows
                return self._handle_windows_path(file_path, path_obj)
            else:
                # On Unix-like systems, try to resolve the path
                try:
                    real_path = os.path.realpath(file_path)
                    if real_path != file_path:
                        self.logger.debug(f"Resolved path: {file_path} -> {real_path}")
                        return real_path
                except Exception as e:
                    self.logger.debug(f"Could not resolve real path: {e}")
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error normalizing file path: {e}")
            return file_path
    
    def _handle_windows_path(self, file_path: str, path_obj: Path) -> str:
        """
        Handle Windows-specific path issues.
        
        Args:
            file_path: Original file path
            path_obj: Path object for the file
            
        Returns:
            Normalized path for Windows
        """
        # Check if path contains Chinese or other non-ASCII characters
        has_non_ascii = any(ord(char) > 127 for char in file_path)
        
        if has_non_ascii:
            self.logger.info("Detected non-ASCII characters in path, creating temporary copy")
            try:
                # Create a temporary file with ASCII name
                temp_name = f"ocr_temp_{hash(file_path) % 10000}{path_obj.suffix}"
                temp_path = self.temp_manager.create_temp_file(
                    suffix=path_obj.suffix,
                    prefix="path_norm_"
                )
                
                # Remove the temp file created by temp_manager and create with our name
                os.remove(temp_path)
                temp_dir = os.path.dirname(temp_path)
                final_temp_path = os.path.join(temp_dir, temp_name)
                
                # Copy the file to temp location
                shutil.copy2(file_path, final_temp_path)
                self.logger.info(f"Created temporary copy for non-ASCII path: {final_temp_path}")
                
                # Add to temp files for cleanup
                self.temp_manager.add_temp_file(final_temp_path)
                
                return final_temp_path
                
            except Exception as e:
                self.logger.error(f"Failed to create temporary copy: {e}")
                return file_path
        
        # Try to resolve the path to handle encoding issues
        try:
            real_path = os.path.realpath(file_path)
            if real_path != file_path:
                self.logger.debug(f"Resolved Windows path: {file_path} -> {real_path}")
                return real_path
        except Exception as e:
            self.logger.debug(f"Could not resolve Windows real path: {e}")
        
        return file_path
    
    def is_path_problematic(self, file_path: str) -> bool:
        """
        Check if a file path might cause issues with processing libraries.
        
        Args:
            file_path: File path to check
            
        Returns:
            True if the path might cause issues, False otherwise
        """
        if not file_path:
            return False
        
        # Check for non-ASCII characters on Windows
        if os.name == 'nt':
            return any(ord(char) > 127 for char in file_path)
        
        # On other systems, check for other potential issues
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
        return any(char in file_path for char in problematic_chars)
    
    def get_safe_filename(self, filename: str, max_length: int = 255) -> str:
        """
        Generate a safe filename from an input string.
        
        Args:
            filename: Original filename
            max_length: Maximum allowed filename length
            
        Returns:
            Safe filename that can be used on most filesystems
        """
        if not filename:
            return "unnamed_file"
        
        # Replace problematic characters
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in '.-_':
                safe_chars.append(char)
            else:
                safe_chars.append('_')
        
        safe_name = ''.join(safe_chars)
        
        # Trim to max length while preserving extension
        if len(safe_name) > max_length:
            name_part, ext_part = os.path.splitext(safe_name)
            max_name_length = max_length - len(ext_part)
            safe_name = name_part[:max_name_length] + ext_part
        
        # Ensure it's not empty
        if not safe_name or safe_name.startswith('.'):
            safe_name = "file_" + safe_name
        
        return safe_name


# Global instance for convenience
_global_normalizer = None


def get_path_normalizer() -> PathNormalizer:
    """
    Get the global path normalizer instance.
    
    Returns:
        Global PathNormalizer instance
    """
    global _global_normalizer
    if _global_normalizer is None:
        _global_normalizer = PathNormalizer()
    return _global_normalizer


def normalize_file_path(file_path: str) -> str:
    """
    Convenience function to normalize a file path.
    
    Args:
        file_path: Path to normalize
        
    Returns:
        Normalized file path
    """
    normalizer = get_path_normalizer()
    return normalizer.normalize_path(file_path)