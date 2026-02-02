"""
PowerPoint presentation to PDF conversion strategy using COM automation.
"""

import logging
import os
import time
from typing import Any

from ..com_manager import get_com_manager
from .base import ConversionStrategy


class PowerPointComStrategy(ConversionStrategy):
    """
    Strategy for converting PowerPoint presentations using COM automation.

    This strategy works for both .ppt and .pptx files and requires
    Microsoft PowerPoint to be installed.
    """

    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert PowerPoint presentation to PDF using PowerPoint COM automation.

        Args:
            input_path: Path to input PowerPoint file (.ppt, .pptx)
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
        presentation = None

        try:
            # Get shared PowerPoint application instance
            com_manager = get_com_manager()
            powerpoint = com_manager.get_powerpoint_app()

            # Open presentation
            presentation = powerpoint.Presentations.Open(
                os.path.abspath(input_path), ReadOnly=True, Untitled=True, WithWindow=False
            )

            # Use SaveAs method with PDF format (more reliable than ExportAsFixedFormat)
            presentation.SaveAs(
                os.path.abspath(output_path),
                32,  # PDF format
            )

            result["success"] = True
            logging.info(f"Successfully converted {input_path} to PDF using PowerPoint COM")

        except Exception as e:
            result["error"] = f"PowerPoint COM conversion error: {str(e)}"
            logging.error(f"PowerPoint COM conversion failed for {input_path}: {e}")

            # Provide more specific error context
            if "file format" in str(e).lower():
                result["error"] += " (File format may be corrupted or unsupported)"
            elif "automation" in str(e).lower() or "dispatch" in str(e).lower():
                result["error"] += " (PowerPoint application not available or COM error)"
            elif "access" in str(e).lower() or "permission" in str(e).lower():
                result["error"] += (
                    " (File access denied - check if file is open in another application)"
                )

        finally:
            # Only close the presentation, not the application
            # The application will be reused for subsequent conversions
            try:
                if presentation:
                    presentation.Close()
                    logging.debug("Closed PowerPoint presentation")
            except Exception as e:
                logging.debug(f"Error closing presentation: {e}")

        result["processing_time"] = time.time() - start_time
        return result

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.

        Args:
            file_extension: File extension

        Returns:
            True for .ppt and .pptx files
        """
        return file_extension.lower() in [".ppt", ".pptx"]

    def get_method_name(self) -> str:
        """Get the name of this conversion method."""
        return "powerpoint_com"
