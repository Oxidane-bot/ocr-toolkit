"""
Quality evaluator module for comparing MarkItDown and OCR processing results.

This module provides intelligent quality assessment to automatically choose
the best processing method for each document.
"""

import re
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class QualityEvaluator:
    """Evaluates and compares the quality of document processing results."""
    
    def __init__(self):
        self.weights = {
            # File type processing preferences (higher = better suited)
            'markitdown_preference': {
                '.docx': 1.3, '.pptx': 1.3, '.xlsx': 1.2,
                '.pdf': 0.8, '.doc': 0.9, '.ppt': 0.9, '.xls': 0.9,
                '.html': 1.2, '.htm': 1.2, '.rtf': 1.1
            },
            'ocr_preference': {
                '.jpg': 1.5, '.jpeg': 1.5, '.png': 1.4, '.bmp': 1.3,
                '.tiff': 1.4, '.tif': 1.4, '.gif': 1.2,
                '.pdf': 1.1  # PDFs could be scanned
            }
        }
    
    def calculate_text_quality_score(self, text: str) -> Dict[str, float]:
        """
        Calculate various quality metrics for processed text.
        
        Args:
            text: The processed text content
            
        Returns:
            Dictionary with quality metrics
        """
        if not text or not text.strip():
            return {
                'length_score': 0,
                'structure_score': 0, 
                'diversity_score': 0,
                'error_penalty': 1.0,
                'total_score': 0
            }
        
        text = text.strip()
        
        # 1. Length score (more content generally better)
        length_score = min(len(text) / 1000, 10) * 10  # Max 100, normalized by 1000 chars
        
        # 2. Structure score (headers, lists, paragraphs)
        structure_indicators = 0
        
        # Headers (markdown format)
        headers = len(re.findall(r'^#+\s', text, re.MULTILINE))
        structure_indicators += min(headers * 5, 30)
        
        # Lists and bullet points
        lists = len(re.findall(r'^[-*•]\s|^\d+\.\s', text, re.MULTILINE))
        structure_indicators += min(lists * 2, 20)
        
        # Paragraph breaks (double newlines)
        paragraphs = len(re.split(r'\n\s*\n', text))
        structure_indicators += min(paragraphs * 1, 20)
        
        # Line breaks (single newlines)
        lines = len([line for line in text.split('\n') if line.strip()])
        structure_indicators += min(lines * 0.5, 30)
        
        structure_score = min(structure_indicators, 100)
        
        # 3. Character diversity score
        unique_chars = len(set(text.lower().replace(' ', '').replace('\n', '')))
        diversity_score = min(unique_chars * 2, 100)
        
        # 4. Error penalty detection
        error_penalty = 1.0
        
        # Detect repetitive patterns (common OCR errors)
        repetitive_patterns = re.findall(r'(.)\1{4,}', text)  # Same char 5+ times
        if repetitive_patterns:
            error_penalty *= 0.8
            
        # Detect excessive special characters
        special_char_ratio = len(re.findall(r'[^\w\s\n.,!?;:()\[\]{}""''-]', text)) / len(text)
        if special_char_ratio > 0.05:  # More than 5% special chars
            error_penalty *= 0.9
            
        # Detect very short "words" (potential OCR artifacts)
        words = re.findall(r'\b\w+\b', text)
        if words:
            very_short_words = len([w for w in words if len(w) == 1])
            short_word_ratio = very_short_words / len(words)
            if short_word_ratio > 0.3:  # More than 30% single-char words
                error_penalty *= 0.7
        
        # 5. Calculate total score
        base_score = (length_score * 0.3 + structure_score * 0.4 + diversity_score * 0.3)
        total_score = base_score * error_penalty
        
        return {
            'length_score': length_score,
            'structure_score': structure_score,
            'diversity_score': diversity_score, 
            'error_penalty': error_penalty,
            'total_score': total_score
        }
    
    def get_file_type_preference(self, file_path: str) -> Dict[str, float]:
        """
        Get processing method preferences based on file type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with method preferences
        """
        ext = Path(file_path).suffix.lower()
        
        markitdown_pref = self.weights['markitdown_preference'].get(ext, 1.0)
        ocr_pref = self.weights['ocr_preference'].get(ext, 1.0)
        
        return {
            'markitdown_preference': markitdown_pref,
            'ocr_preference': ocr_pref
        }
    
    def compare_results(self, markitdown_result: Dict[str, Any], 
                       ocr_result: Dict[str, Any], 
                       file_path: str) -> Dict[str, Any]:
        """
        Compare MarkItDown and OCR results and choose the best one.
        
        Args:
            markitdown_result: Result from MarkItDown processing
            ocr_result: Result from OCR processing
            file_path: Path to the original file
            
        Returns:
            Dictionary with comparison results and chosen method
        """
        comparison = {
            'file_path': file_path,
            'chosen_method': 'ocr',  # default fallback
            'markitdown_score': 0,
            'ocr_score': 0,
            'markitdown_available': False,
            'ocr_available': False,
            'selection_reason': 'No valid results',
            'quality_details': {}
        }
        
        # Check if results are available and successful
        md_available = (markitdown_result and 
                       markitdown_result.get('success', False) and 
                       bool(markitdown_result.get('content')))
        ocr_available = (ocr_result and 
                        ocr_result.get('success', False) and
                        bool(ocr_result.get('content')))
        
        comparison['markitdown_available'] = md_available
        comparison['ocr_available'] = ocr_available
        
        # If only one method succeeded, use that one
        if md_available and not ocr_available:
            comparison['chosen_method'] = 'markitdown'
            comparison['selection_reason'] = 'Only MarkItDown succeeded'
            return comparison
        elif ocr_available and not md_available:
            comparison['chosen_method'] = 'ocr'
            comparison['selection_reason'] = 'Only OCR succeeded'
            return comparison
        elif not md_available and not ocr_available:
            comparison['selection_reason'] = 'Both methods failed'
            return comparison
        
        # Both methods succeeded - compare quality
        md_text = markitdown_result['content']
        ocr_text = ocr_result['content']
        
        # Calculate quality scores
        md_quality = self.calculate_text_quality_score(md_text)
        ocr_quality = self.calculate_text_quality_score(ocr_text)
        
        # Apply file type preferences
        file_prefs = self.get_file_type_preference(file_path)
        
        # Calculate final weighted scores
        md_final_score = md_quality['total_score'] * file_prefs['markitdown_preference']
        ocr_final_score = ocr_quality['total_score'] * file_prefs['ocr_preference']
        
        comparison['markitdown_score'] = md_final_score
        comparison['ocr_score'] = ocr_final_score
        comparison['quality_details'] = {
            'markitdown_quality': md_quality,
            'ocr_quality': ocr_quality,
            'file_preferences': file_prefs
        }
        
        # Choose the better method
        if md_final_score > ocr_final_score:
            comparison['chosen_method'] = 'markitdown'
            score_diff = md_final_score - ocr_final_score
            comparison['selection_reason'] = f'MarkItDown scored {md_final_score:.1f} vs OCR {ocr_final_score:.1f} (+{score_diff:.1f})'
        else:
            comparison['chosen_method'] = 'ocr'
            score_diff = ocr_final_score - md_final_score
            comparison['selection_reason'] = f'OCR scored {ocr_final_score:.1f} vs MarkItDown {md_final_score:.1f} (+{score_diff:.1f})'
        
        return comparison
    
    def format_comparison_summary(self, comparison: Dict[str, Any]) -> str:
        """
        Format a human-readable comparison summary.
        
        Args:
            comparison: Result from compare_results()
            
        Returns:
            Formatted summary string
        """
        file_name = os.path.basename(comparison['file_path'])
        method = comparison['chosen_method'].upper()
        reason = comparison['selection_reason']
        
        summary = f"📄 {file_name}: Selected {method} - {reason}"
        
        if comparison['markitdown_available'] and comparison['ocr_available']:
            md_score = comparison['markitdown_score']
            ocr_score = comparison['ocr_score']
            summary += f"\\n   Quality scores: MarkItDown={md_score:.1f}, OCR={ocr_score:.1f}"
        
        return summary


def create_quality_evaluator() -> QualityEvaluator:
    """Factory function to create a quality evaluator instance."""
    return QualityEvaluator()