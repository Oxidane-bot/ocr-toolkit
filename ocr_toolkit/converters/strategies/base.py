"""
Base strategy interface for Office document conversion.
"""

from abc import ABC, abstractmethod
from typing import Any


class ConversionStrategy(ABC):
    """Abstract base class for Office document conversion strategies."""

    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert document using this strategy.

        Args:
            input_path: Path to input file
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results containing:
            - method: Name of the conversion method
            - success: Boolean indicating success
            - processing_time: Time taken in seconds
            - error: Error message if failed
        """
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.

        Args:
            file_extension: File extension (e.g., '.docx')

        Returns:
            True if supported, False otherwise
        """
        pass

    @abstractmethod
    def get_method_name(self) -> str:
        """
        Get the name of this conversion method.

        Returns:
            String identifier for this method
        """
        pass
