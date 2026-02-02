"""
Word document to PDF conversion strategy using COM automation.
"""

import logging
import os
import time
from typing import Any

from ..com_manager import get_com_manager
from .base import ConversionStrategy


class WordComStrategy(ConversionStrategy):
    """
    Strategy for converting Word documents using COM automation.

    This strategy works for both .doc and .docx files and requires
    Microsoft Word to be installed.
    """

    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert Word document to PDF using Word COM automation.

        Args:
            input_path: Path to input Word file (.doc, .docx)
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results
        """
        result = {
            "method": self.get_method_name(),
            "success": False,
            "processing_time": 0,
            "error": "",
        }

        start_time = time.time()
        doc = None

        try:
            # Get shared Word application instance
            com_manager = get_com_manager()
            word = com_manager.get_word_app()

            # Open document
            doc = word.Documents.Open(os.path.abspath(input_path))

            # Export as PDF (format 17 = PDF)
            doc.ExportAsFixedFormat(
                OutputFileName=os.path.abspath(output_path),
                ExportFormat=17,  # PDF format
                OpenAfterExport=False,
                OptimizeFor=0,  # Print optimization
                BitmapMissingFonts=True,
                DocStructureTags=True,
                CreateBookmarks=0,
            )

            result["success"] = True
            logging.info(f"Successfully converted {input_path} to PDF using Word COM")

        except Exception as e:
            result["error"] = str(e)
            logging.error(f"Word COM conversion failed for {input_path}: {e}")

        finally:
            # Only close the document, not the application
            # The application will be reused for subsequent conversions
            try:
                if doc:
                    doc.Close()
            except Exception:
                pass

        result["processing_time"] = time.time() - start_time
        return result

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.

        Args:
            file_extension: File extension

        Returns:
            True for .doc and .docx files
        """
        return file_extension.lower() in [".doc", ".docx"]

    def get_method_name(self) -> str:
        """Get the name of this conversion method."""
        return "word_com"
