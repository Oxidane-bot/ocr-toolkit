"""
MarkItDown document processor module.

This module provides a high-level interface for processing documents
using the MarkItDown library.
"""

import os
import time
import logging
from typing import Dict, Any

from markitdown import MarkItDown


def process_single_document(file_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Process a single document with MarkItDown.

    Args:
        file_path: Path to input file
        output_dir: Directory for output markdown file

    Returns:
        Dictionary with processing results
    """
    result = {
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'success': False,
        'processing_time': 0,
        'output_file': '',
        'output_size': 0,
        'text_length': 0,
        'error': ''
    }

    start_time = time.time()

    try:
        # Initialize MarkItDown
        md = MarkItDown()

        # Process the document
        markdown_result = md.convert(file_path)
        markdown_text = markdown_result.text_content

        # Generate output filename
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}.md")

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Save markdown output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_text)

        # Update result
        result['success'] = True
        result['output_file'] = output_file
        result['output_size'] = os.path.getsize(output_file)
        result['text_length'] = len(markdown_text)

        logging.info(f"✓ Processed: {os.path.basename(file_path)} -> {os.path.basename(output_file)}")

    except Exception as e:
        result['error'] = str(e)
        logging.error(f"✗ Failed to process {file_path}: {e}")

    result['processing_time'] = time.time() - start_time
    return result