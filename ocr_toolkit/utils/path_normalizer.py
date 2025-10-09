"""
Path normalization service for handling file paths across different platforms.

This module provides utilities for normalizing file paths to handle
character encoding issues, especially with Chinese characters on Windows.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import config
from ..utils.temp_file_manager import get_temp_manager


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


def timeout_wrapper(func: Callable, timeout_seconds: int = 60, *args, **kwargs) -> Any:
    """
    Execute a function with a timeout using threading.

    Args:
        func: Function to execute
        timeout_seconds: Timeout in seconds
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Function result

    Raises:
        TimeoutError: If the function doesn't complete within the timeout
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Thread is still running, timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")

    if exception[0]:
        raise exception[0]

    return result[0]


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

    def _is_file_locked(self, file_path: str) -> bool:
        """
        Check if a file is locked by another process.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is locked, False otherwise
        """
        try:
            # Try to open the file in read mode
            with open(file_path, 'rb') as f:
                # Try to acquire an exclusive lock (Windows specific check)
                import msvcrt
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    return False
                except OSError:
                    return True
        except (OSError, ImportError):
            # If we can't determine, assume it's not locked
            return False

    def _safe_copy_file(self, source: str, destination: str, chunk_size: int = 8192) -> None:
        """
        Safely copy a file with progress monitoring and lock detection.

        Args:
            source: Source file path
            destination: Destination file path
            chunk_size: Size of each read/write chunk in bytes

        Raises:
            OSError: If the file cannot be copied
            TimeoutError: If the operation takes too long
        """
        # Check if source file is locked
        if self._is_file_locked(source):
            raise OSError(f"Source file is locked by another process: {source}")

        source_size = os.path.getsize(source)
        copied_bytes = 0

        try:
            with open(source, 'rb') as src, open(destination, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break

                    dst.write(chunk)
                    copied_bytes += len(chunk)

                    # Log progress for large files
                    if source_size > 10 * 1024 * 1024:  # > 10MB
                        progress = (copied_bytes / source_size) * 100
                        if copied_bytes % (1024 * 1024) == 0:  # Every MB
                            self.logger.debug(f"Copy progress: {progress:.1f}% ({copied_bytes}/{source_size} bytes)")

                    # Yield control to allow timeout mechanism to work
                    time.sleep(0.001)  # 1ms sleep to prevent tight loop

            # Verify the copy was successful
            if os.path.getsize(destination) != source_size:
                raise OSError(f"File copy incomplete: expected {source_size} bytes, got {os.path.getsize(destination)} bytes")

        except Exception as e:
            # Clean up partial file on error
            try:
                if os.path.exists(destination):
                    os.remove(destination)
            except Exception:
                pass
            raise OSError(f"File copy failed: {e}") from e


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
        has_non_ascii = any(ord(char) > config.ASCII_BOUNDARY for char in file_path)

        if has_non_ascii:
            self.logger.info("Detected non-ASCII characters in path, creating temporary copy")
            try:
                # Get file size for logging
                file_size = path_obj.stat().st_size
                self.logger.info(f"File size: {file_size / (1024*1024):.2f} MB")

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

                # Copy the file to temp location with timeout protection
                self.logger.info(f"Starting file copy: {file_path} -> {final_temp_path}")
                start_time = time.time()

                # Use safe copy method with timeout wrapper for better control
                timeout_wrapper(self._safe_copy_file, 120, file_path, final_temp_path)

                copy_time = time.time() - start_time
                self.logger.info(f"File copy completed in {copy_time:.2f} seconds")
                self.logger.info(f"Created temporary copy for non-ASCII path: {final_temp_path}")

                # Add to temp files for cleanup
                self.temp_manager.add_temp_file(final_temp_path)

                return final_temp_path

            except TimeoutError as e:
                self.logger.error(f"File copy operation timed out: {e}")
                self.logger.error(f"Skipping file due to timeout: {file_path}")
                return file_path
            except OSError as e:
                if "locked by another process" in str(e):
                    self.logger.error(f"File is locked by another process: {file_path}")
                    self.logger.error("Please close any applications that might be using this file and try again")
                else:
                    self.logger.error(f"File operation failed: {e}")
                return file_path
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
            return any(ord(char) > config.ASCII_BOUNDARY for char in file_path)

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
