"""
Document converters module.

This module provides various document conversion strategies and interfaces
for converting between different document formats.
"""

from .office_converter import OfficeConverter, get_office_converter, convert_office_to_pdf, create_temp_pdf

__all__ = ['OfficeConverter', 'get_office_converter', 'convert_office_to_pdf', 'create_temp_pdf']