"""
Base classes for document processors.

This module defines the abstract base class and result types for all document processors
to ensure consistent interfaces and error handling across the toolkit.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ProcessingResult:
    """
    Standardized result object for document processing operations.

    This class provides a consistent interface for all processing results,
    making it easier to handle responses from different processors.
    """
    success: bool
    content: str
    processing_time: float
    method: str
    error: str = ''
    file_path: str = ''
    file_name: str = ''
    pages: int = 0
    temp_files: list[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Initialize optional fields with empty defaults."""
        if self.temp_files is None:
            self.temp_files = []
        if self.metadata is None:
            self.metadata = {}

        # Set file_name from file_path if not provided
        if self.file_path and not self.file_name:
            self.file_name = os.path.basename(self.file_path)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for backward compatibility."""
        return {
            'success': self.success,
            'content': self.content,
            'processing_time': self.processing_time,
            'method': self.method,
            'error': self.error,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'pages': self.pages,
            'temp_files': self.temp_files,
            'metadata': self.metadata
        }


class FileProcessorBase(ABC):
    """
    Abstract base class for all document processors.

    This class defines the common interface that all processors must implement,
    ensuring consistent behavior and error handling across different processing methods.
    """

    def __init__(self):
        """Initialize the processor."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """
        Process a document file.

        Args:
            file_path: Path to the document file
            **kwargs: Additional processing parameters

        Returns:
            ProcessingResult object with processing results
        """
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this processor supports the given file format.

        Args:
            file_extension: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if the format is supported, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported file formats.

        Returns:
            List of supported file extensions
        """
        pass

    def _create_result(self, file_path: str, method: str, start_time: float) -> ProcessingResult:
        """
        Create a base ProcessingResult object with common fields.

        Args:
            file_path: Path to the processed file
            method: Processing method name
            start_time: Processing start time

        Returns:
            ProcessingResult object with basic fields populated
        """
        return ProcessingResult(
            success=False,
            content='',
            processing_time=time.time() - start_time,
            method=method,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            error='',
            pages=0,
            temp_files=[],
            metadata={}
        )

    def _handle_exception(self, e: Exception, result: ProcessingResult) -> ProcessingResult:
        """
        Handle exceptions during processing.

        Args:
            e: The exception that occurred
            result: The ProcessingResult object to update

        Returns:
            Updated ProcessingResult with error information
        """
        error_msg = str(e)
        result.error = error_msg
        result.success = False

        self.logger.debug(f"{self.__class__.__name__} failed for {result.file_path}: {error_msg}")

        return result

    def _validate_file(self, file_path: str) -> bool:
        """
        Validate that the file exists and is readable.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if file is valid, False otherwise
        """
        if not file_path:
            return False

        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False

        if not path.is_file():
            self.logger.error(f"Path is not a file: {file_path}")
            return False

        try:
            # Test if file is readable
            with open(file_path, 'rb') as f:
                f.read(1)
            return True
        except (OSError, PermissionError) as e:
            self.logger.error(f"Cannot read file {file_path}: {e}")
            return False
