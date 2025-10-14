"""
Excel workbook to PDF conversion strategy using COM automation.
"""

import logging
import os
import time
from typing import Any

from .base import ConversionStrategy


class ExcelComStrategy(ConversionStrategy):
    """
    Strategy for converting Excel workbooks using COM automation.

    This strategy works for both .xls and .xlsx files and requires
    Microsoft Excel to be installed.
    """

    def convert(self, input_path: str, output_path: str) -> dict[str, Any]:
        """
        Convert Excel workbook to PDF using Excel COM automation.

        Args:
            input_path: Path to input Excel file (.xls, .xlsx)
            output_path: Path to output PDF file

        Returns:
            Dictionary with conversion results
        """
        result = {
            'method': self.get_method_name(),
            'success': False,
            'processing_time': 0,
            'error': ''
        }

        start_time = time.time()
        excel = None
        workbook = None

        try:
            import win32com.client

            # Create Excel application
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            # Open workbook
            workbook = excel.Workbooks.Open(os.path.abspath(input_path))

            # Export as PDF (format 0 = PDF)
            workbook.ExportAsFixedFormat(
                Type=0,  # PDF format
                Filename=os.path.abspath(output_path),
                Quality=0,  # Standard quality
                IncludeDocProps=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False
            )

            result['success'] = True
            logging.info(f"Successfully converted {input_path} to PDF using Excel COM")

        except Exception as e:
            result['error'] = str(e)
            logging.error(f"Excel COM conversion failed for {input_path}: {e}")

        finally:
            # Clean up COM objects
            try:
                if workbook:
                    workbook.Close()
                if excel:
                    excel.Quit()
            except Exception:
                pass

        result['processing_time'] = time.time() - start_time
        return result

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this strategy supports the given file format.

        Args:
            file_extension: File extension

        Returns:
            True for .xls and .xlsx files
        """
        return file_extension.lower() in ['.xls', '.xlsx']

    def get_method_name(self) -> str:
        """Get the name of this conversion method."""
        return 'excel_com'
