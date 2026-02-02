"""
Unit tests for quality evaluator module.
"""

import os

# Add project root to path
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit.quality_evaluator import QualityEvaluator, create_quality_evaluator


class TestQualityEvaluator:
    """Test cases for QualityEvaluator class."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.evaluator = QualityEvaluator()

    def test_init(self):
        """Test QualityEvaluator initialization."""
        assert self.evaluator is not None
        assert "markitdown_preference" in self.evaluator.weights
        assert "ocr_preference" in self.evaluator.weights

    def test_calculate_text_quality_score_empty_text(self):
        """Test quality score calculation for empty text."""
        result = self.evaluator.calculate_text_quality_score("")

        assert result["total_score"] == 0
        assert result["length_score"] == 0
        assert result["structure_score"] == 0
        assert result["diversity_score"] == 0
        assert result["error_penalty"] == 1.0

    def test_calculate_text_quality_score_whitespace_only(self):
        """Test quality score calculation for whitespace-only text."""
        result = self.evaluator.calculate_text_quality_score("   \n\t  ")

        assert result["total_score"] == 0

    def test_calculate_text_quality_score_normal_text(self):
        """Test quality score calculation for normal text."""
        text = """# Main Title
        
This is a well-formatted document with proper sentences. It contains multiple paragraphs and good structure.

## Section 1

- First bullet point
- Second bullet point  
- Third bullet point

## Section 2

1. First numbered item
2. Second numbered item
3. Third numbered item

This document has good variety and structure."""

        result = self.evaluator.calculate_text_quality_score(text)

        assert isinstance(result, dict)
        assert "total_score" in result
        assert result["total_score"] > 0
        assert result["length_score"] > 0
        assert result["structure_score"] > 0
        assert result["diversity_score"] > 0
        assert result["error_penalty"] > 0

    def test_calculate_text_quality_score_poor_text(self):
        """Test quality score calculation for poor quality text."""
        text = "th1s 1s p00r qu@l1ty t3xt w1th m@ny 3rr0rs!!!!!!"
        result = self.evaluator.calculate_text_quality_score(text)

        assert isinstance(result, dict)
        assert "total_score" in result
        assert result["error_penalty"] < 1.0  # Should have penalty for repetitive patterns

    def test_calculate_text_quality_score_excessive_special_chars(self):
        """Test penalty for excessive special characters."""
        text = "Normal text with @@@@@@@@@@@ way too many ######### special chars!!!"
        result = self.evaluator.calculate_text_quality_score(text)

        # Should have penalty for special characters
        assert result["error_penalty"] < 1.0

    def test_calculate_text_quality_score_short_words(self):
        """Test penalty for too many single-character words."""
        text = "a b c d e f g h i j k l m n o p q r s t u v w x y z " * 10
        result = self.evaluator.calculate_text_quality_score(text)

        # Should have penalty for too many single-char words
        assert result["error_penalty"] < 1.0

    def test_quality_metrics_components(self):
        """Test individual quality metric components."""
        text = "# Title\n\nThis is a test document with proper formatting.\n\n- List item 1\n- List item 2"
        result = self.evaluator.calculate_text_quality_score(text)

        # Check that all expected metrics are present
        expected_metrics = [
            "length_score",
            "structure_score",
            "diversity_score",
            "error_penalty",
            "total_score",
        ]
        for metric in expected_metrics:
            assert metric in result
            assert isinstance(result[metric], (int, float))
            assert result[metric] >= 0

    @pytest.mark.parametrize("text_length", [10, 100, 1000, 5000])
    def test_quality_score_different_lengths(self, text_length):
        """Test quality score calculation for different text lengths."""
        text = "This is a test sentence with good structure. " * (text_length // 45 + 1)
        text = text[:text_length]

        result = self.evaluator.calculate_text_quality_score(text)
        assert isinstance(result["total_score"], (int, float))
        assert result["total_score"] >= 0

    def test_get_file_type_preference_docx(self):
        """Test file type preference for DOCX files."""
        result = self.evaluator.get_file_type_preference("test.docx")

        assert "markitdown_preference" in result
        assert "ocr_preference" in result
        assert result["markitdown_preference"] > 1.0  # DOCX should prefer MarkItDown

    def test_get_file_type_preference_jpg(self):
        """Test file type preference for image files."""
        result = self.evaluator.get_file_type_preference("test.jpg")

        assert result["ocr_preference"] > 1.0  # Images should prefer OCR

    def test_get_file_type_preference_unknown(self):
        """Test file type preference for unknown formats."""
        result = self.evaluator.get_file_type_preference("test.unknown")

        assert result["markitdown_preference"] == 1.0  # Default preference
        assert result["ocr_preference"] == 1.0

    def test_compare_results_both_successful(self):
        """Test comparison when both methods succeed."""
        md_result = {
            "success": True,
            "content": "# Good Document\n\nThis is well-structured content with headers and proper formatting.",
        }

        ocr_result = {"success": True, "content": "Poor OCR result with bad formatting and errors."}

        file_path = "test.docx"

        result = self.evaluator.compare_results(md_result, ocr_result, file_path)

        assert "chosen_method" in result
        assert "markitdown_score" in result
        assert "ocr_score" in result
        assert result["markitdown_available"] == True
        assert result["ocr_available"] == True
        assert "selection_reason" in result

    def test_compare_results_only_markitdown_succeeds(self):
        """Test comparison when only MarkItDown succeeds."""
        md_result = {"success": True, "content": "Good content"}
        ocr_result = {"success": False, "content": ""}

        result = self.evaluator.compare_results(md_result, ocr_result, "test.pdf")

        assert result["chosen_method"] == "markitdown"
        assert result["selection_reason"] == "Only MarkItDown succeeded"
        assert result["markitdown_available"] == True
        assert result["ocr_available"] == False

    def test_compare_results_only_ocr_succeeds(self):
        """Test comparison when only OCR succeeds."""
        md_result = {"success": False, "content": ""}
        ocr_result = {"success": True, "content": "OCR content"}

        result = self.evaluator.compare_results(md_result, ocr_result, "test.jpg")

        assert result["chosen_method"] == "ocr"
        assert result["selection_reason"] == "Only OCR succeeded"
        assert result["markitdown_available"] == False
        assert result["ocr_available"] == True

    def test_compare_results_both_failed(self):
        """Test comparison when both methods fail."""
        md_result = {"success": False, "content": ""}
        ocr_result = {"success": False, "content": ""}

        result = self.evaluator.compare_results(md_result, ocr_result, "test.xyz")

        assert result["selection_reason"] == "Both methods failed"
        assert result["markitdown_available"] == False
        assert result["ocr_available"] == False

    def test_compare_results_missing_content(self):
        """Test comparison with missing content in successful results."""
        md_result = {"success": True, "content": None}  # Missing content
        ocr_result = {"success": True, "content": "Valid OCR content"}

        result = self.evaluator.compare_results(md_result, ocr_result, "test.pdf")

        assert result["chosen_method"] == "ocr"
        assert result["selection_reason"] == "Only OCR succeeded"

    def test_format_comparison_summary(self):
        """Test formatting of comparison summary."""
        comparison = {
            "file_path": "/path/to/test_document.pdf",
            "chosen_method": "markitdown",
            "selection_reason": "Better quality score",
            "markitdown_available": True,
            "ocr_available": True,
            "markitdown_score": 85.5,
            "ocr_score": 72.3,
        }

        summary = self.evaluator.format_comparison_summary(comparison)

        assert "test_document.pdf" in summary
        assert "MARKITDOWN" in summary
        assert "Better quality score" in summary
        assert "85.5" in summary
        assert "72.3" in summary

    def test_format_comparison_summary_single_method(self):
        """Test formatting summary when only one method available."""
        comparison = {
            "file_path": "/path/to/image.jpg",
            "chosen_method": "ocr",
            "selection_reason": "Only OCR succeeded",
            "markitdown_available": False,
            "ocr_available": True,
        }

        summary = self.evaluator.format_comparison_summary(comparison)

        assert "image.jpg" in summary
        assert "OCR" in summary
        assert "Only OCR succeeded" in summary
        # Should not contain quality scores for single method
        assert "Quality scores:" not in summary

    def test_create_quality_evaluator_factory(self):
        """Test factory function."""
        evaluator = create_quality_evaluator()

        assert isinstance(evaluator, QualityEvaluator)
        assert evaluator.weights is not None
