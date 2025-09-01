"""
Results analysis script for OCR vs MarkItDown comparison tests.

This script analyzes the output from comparison_batch_test.py and generates
comprehensive reports comparing the effectiveness of both approaches.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


def setup_logging():
    """Configure logging for the analysis script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def load_results_file(results_file: str) -> Dict[str, Any]:
    """Load results from JSON file."""
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load results file {results_file}: {e}")
        return {}


def find_latest_results(reports_dir: str) -> Optional[str]:
    """Find the most recent results file in the reports directory."""
    if not os.path.exists(reports_dir):
        logging.error(f"Reports directory does not exist: {reports_dir}")
        return None
    
    results_files = [f for f in os.listdir(reports_dir) if f.startswith('comparison_results_') and f.endswith('.json')]
    
    if not results_files:
        logging.error(f"No results files found in {reports_dir}")
        return None
    
    # Sort by timestamp (embedded in filename)
    results_files.sort(reverse=True)
    latest_file = os.path.join(reports_dir, results_files[0])
    logging.info(f"Using latest results file: {latest_file}")
    return latest_file


def calculate_basic_stats(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate basic statistics from the results."""
    if not results.get('results'):
        return {}
    
    total_files = len(results['results'])
    ocr_results = [r['ocr_result'] for r in results['results']]
    md_results = [r['markitdown_result'] for r in results['results']]
    
    # Success rates
    ocr_successes = sum(1 for r in ocr_results if r['success'])
    md_successes = sum(1 for r in md_results if r['success'])
    
    # Processing times (only for successful attempts)
    ocr_times = [r['processing_time'] for r in ocr_results if r['success']]
    md_times = [r['processing_time'] for r in md_results if r['success']]
    
    # Output sizes and text lengths (only for successful attempts)
    ocr_sizes = [r['output_size'] for r in ocr_results if r['success']]
    md_sizes = [r['output_size'] for r in md_results if r['success']]
    ocr_text_lengths = [r['text_length'] for r in ocr_results if r['success']]
    md_text_lengths = [r['text_length'] for r in md_results if r['success']]
    
    stats = {
        'total_files': total_files,
        'ocr_success_rate': ocr_successes / total_files if total_files > 0 else 0,
        'markitdown_success_rate': md_successes / total_files if total_files > 0 else 0,
        'ocr_successes': ocr_successes,
        'markitdown_successes': md_successes,
        'processing_times': {
            'ocr': {
                'total': sum(ocr_times),
                'average': statistics.mean(ocr_times) if ocr_times else 0,
                'median': statistics.median(ocr_times) if ocr_times else 0,
                'min': min(ocr_times) if ocr_times else 0,
                'max': max(ocr_times) if ocr_times else 0
            },
            'markitdown': {
                'total': sum(md_times),
                'average': statistics.mean(md_times) if md_times else 0,
                'median': statistics.median(md_times) if md_times else 0,
                'min': min(md_times) if md_times else 0,
                'max': max(md_times) if md_times else 0
            }
        },
        'output_sizes': {
            'ocr': {
                'average': statistics.mean(ocr_sizes) if ocr_sizes else 0,
                'median': statistics.median(ocr_sizes) if ocr_sizes else 0,
                'total': sum(ocr_sizes)
            },
            'markitdown': {
                'average': statistics.mean(md_sizes) if md_sizes else 0,
                'median': statistics.median(md_sizes) if md_sizes else 0,
                'total': sum(md_sizes)
            }
        },
        'text_lengths': {
            'ocr': {
                'average': statistics.mean(ocr_text_lengths) if ocr_text_lengths else 0,
                'median': statistics.median(ocr_text_lengths) if ocr_text_lengths else 0,
                'total': sum(ocr_text_lengths)
            },
            'markitdown': {
                'average': statistics.mean(md_text_lengths) if md_text_lengths else 0,
                'median': statistics.median(md_text_lengths) if md_text_lengths else 0,
                'total': sum(md_text_lengths)
            }
        }
    }
    
    return stats


def analyze_by_file_type(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze results broken down by file type."""
    if not results.get('results'):
        return {}
    
    # Group results by file extension
    by_extension = {}
    for result in results['results']:
        ext = result['file_extension']
        if ext not in by_extension:
            by_extension[ext] = []
        by_extension[ext].append(result)
    
    analysis = {}
    for ext, ext_results in by_extension.items():
        total = len(ext_results)
        ocr_successes = sum(1 for r in ext_results if r['ocr_result']['success'])
        md_successes = sum(1 for r in ext_results if r['markitdown_result']['success'])
        
        # Average processing times for successful attempts
        ocr_times = [r['ocr_result']['processing_time'] for r in ext_results if r['ocr_result']['success']]
        md_times = [r['markitdown_result']['processing_time'] for r in ext_results if r['markitdown_result']['success']]
        
        analysis[ext] = {
            'total_files': total,
            'ocr_success_rate': ocr_successes / total if total > 0 else 0,
            'markitdown_success_rate': md_successes / total if total > 0 else 0,
            'ocr_avg_time': statistics.mean(ocr_times) if ocr_times else 0,
            'markitdown_avg_time': statistics.mean(md_times) if md_times else 0,
            'ocr_successes': ocr_successes,
            'markitdown_successes': md_successes
        }
    
    return analysis


def analyze_failure_patterns(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze common failure patterns and errors."""
    if not results.get('results'):
        return {}
    
    ocr_errors = {}
    md_errors = {}
    
    for result in results['results']:
        # OCR errors
        if not result['ocr_result']['success'] and result['ocr_result']['error']:
            error = result['ocr_result']['error']
            if error not in ocr_errors:
                ocr_errors[error] = []
            ocr_errors[error].append(result['file_name'])
        
        # MarkItDown errors
        if not result['markitdown_result']['success'] and result['markitdown_result']['error']:
            error = result['markitdown_result']['error']
            if error not in md_errors:
                md_errors[error] = []
            md_errors[error].append(result['file_name'])
    
    return {
        'ocr_errors': {error: len(files) for error, files in ocr_errors.items()},
        'markitdown_errors': {error: len(files) for error, files in md_errors.items()},
        'ocr_error_details': ocr_errors,
        'markitdown_error_details': md_errors
    }


def generate_recommendations(stats: Dict[str, Any], by_type: Dict[str, Any], 
                           failures: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on the analysis."""
    recommendations = []
    
    # Overall success rate comparison
    ocr_rate = stats.get('ocr_success_rate', 0)
    md_rate = stats.get('markitdown_success_rate', 0)
    
    if md_rate > ocr_rate + 0.1:  # More than 10% better
        recommendations.append(
            f"MarkItDown shows significantly higher success rate ({md_rate:.1%} vs {ocr_rate:.1%}). "
            "Consider MarkItDown as primary method for mixed document types."
        )
    elif ocr_rate > md_rate + 0.1:
        recommendations.append(
            f"OCR shows significantly higher success rate ({ocr_rate:.1%} vs {md_rate:.1%}). "
            "OCR pipeline may be more reliable for your document types."
        )
    else:
        recommendations.append(
            "Both methods show similar success rates. Choice should be based on other factors like speed and quality."
        )
    
    # Speed comparison
    ocr_avg_time = stats.get('processing_times', {}).get('ocr', {}).get('average', 0)
    md_avg_time = stats.get('processing_times', {}).get('markitdown', {}).get('average', 0)
    
    if ocr_avg_time > 0 and md_avg_time > 0:
        if md_avg_time < ocr_avg_time * 0.5:  # More than 2x faster
            recommendations.append(
                f"MarkItDown is significantly faster ({md_avg_time:.2f}s vs {ocr_avg_time:.2f}s average). "
                "Consider MarkItDown for high-volume processing."
            )
        elif ocr_avg_time < md_avg_time * 0.5:
            recommendations.append(
                f"OCR is significantly faster ({ocr_avg_time:.2f}s vs {md_avg_time:.2f}s average). "
                "OCR may be better for time-sensitive tasks."
            )
    
    # File type specific recommendations
    pdf_only_files = [ext for ext, data in by_type.items() if ext == '.pdf']
    office_files = [ext for ext, data in by_type.items() if ext in ['.docx', '.pptx', '.xlsx']]
    
    if office_files:
        office_md_success = sum(by_type[ext]['markitdown_success_rate'] for ext in office_files) / len(office_files)
        office_ocr_success = sum(by_type[ext]['ocr_success_rate'] for ext in office_files) / len(office_files)
        
        if office_md_success > office_ocr_success + 0.2:
            recommendations.append(
                "For Office documents (DOCX, PPTX, XLSX), MarkItDown shows superior performance. "
                "Use MarkItDown for these formats."
            )
    
    # Failure pattern recommendations
    if failures.get('ocr_errors'):
        most_common_ocr_error = max(failures['ocr_errors'].items(), key=lambda x: x[1])
        if 'only supports PDF' in most_common_ocr_error[0]:
            recommendations.append(
                "OCR pipeline is limited to PDF files. Use MarkItDown for other document formats."
            )
    
    return recommendations


def generate_html_report(stats: Dict[str, Any], by_type: Dict[str, Any], 
                        failures: Dict[str, Any], recommendations: List[str],
                        output_file: str) -> None:
    """Generate an HTML report with the analysis results."""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OCR vs MarkItDown Comparison Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                line-height: 1.6;
            }}
            .header {{
                background-color: #f4f4f4;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .section {{
                margin-bottom: 30px;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            .metric {{
                display: inline-block;
                margin: 10px;
                padding: 15px;
                background-color: #f9f9f9;
                border-radius: 5px;
                min-width: 200px;
            }}
            .success {{ background-color: #d4edda; }}
            .warning {{ background-color: #fff3cd; }}
            .error {{ background-color: #f8d7da; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            .recommendation {{
                background-color: #e7f3ff;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #007bff;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>OCR vs MarkItDown Comparison Report</h1>
            <p>Analysis of document processing performance across different file types</p>
        </div>
        
        <div class="section">
            <h2>Overall Statistics</h2>
            <div class="metric">
                <strong>Total Files:</strong> {stats.get('total_files', 0)}
            </div>
            <div class="metric">
                <strong>OCR Success Rate:</strong> {stats.get('ocr_success_rate', 0):.1%}
            </div>
            <div class="metric">
                <strong>MarkItDown Success Rate:</strong> {stats.get('markitdown_success_rate', 0):.1%}
            </div>
        </div>
        
        <div class="section">
            <h2>Processing Time Comparison</h2>
            <table>
                <tr>
                    <th>Method</th>
                    <th>Total Time (s)</th>
                    <th>Average Time (s)</th>
                    <th>Median Time (s)</th>
                    <th>Min Time (s)</th>
                    <th>Max Time (s)</th>
                </tr>
                <tr>
                    <td>OCR</td>
                    <td>{stats.get('processing_times', {}).get('ocr', {}).get('total', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('ocr', {}).get('average', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('ocr', {}).get('median', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('ocr', {}).get('min', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('ocr', {}).get('max', 0):.2f}</td>
                </tr>
                <tr>
                    <td>MarkItDown</td>
                    <td>{stats.get('processing_times', {}).get('markitdown', {}).get('total', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('markitdown', {}).get('average', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('markitdown', {}).get('median', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('markitdown', {}).get('min', 0):.2f}</td>
                    <td>{stats.get('processing_times', {}).get('markitdown', {}).get('max', 0):.2f}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Results by File Type</h2>
            <table>
                <tr>
                    <th>File Type</th>
                    <th>Files</th>
                    <th>OCR Success Rate</th>
                    <th>MarkItDown Success Rate</th>
                    <th>OCR Avg Time (s)</th>
                    <th>MarkItDown Avg Time (s)</th>
                </tr>
    """
    
    for ext, data in by_type.items():
        html_content += f"""
                <tr>
                    <td>{ext}</td>
                    <td>{data['total_files']}</td>
                    <td>{data['ocr_success_rate']:.1%}</td>
                    <td>{data['markitdown_success_rate']:.1%}</td>
                    <td>{data['ocr_avg_time']:.2f}</td>
                    <td>{data['markitdown_avg_time']:.2f}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Recommendations</h2>
    """
    
    for rec in recommendations:
        html_content += f'<div class="recommendation">{rec}</div>\n'
    
    html_content += """
        </div>
        
        <div class="section">
            <h2>Error Analysis</h2>
            <h3>OCR Errors</h3>
    """
    
    if failures.get('ocr_errors'):
        html_content += "<ul>"
        for error, count in failures['ocr_errors'].items():
            html_content += f"<li><strong>{error}:</strong> {count} files</li>"
        html_content += "</ul>"
    else:
        html_content += "<p>No OCR errors recorded.</p>"
    
    html_content += "<h3>MarkItDown Errors</h3>"
    
    if failures.get('markitdown_errors'):
        html_content += "<ul>"
        for error, count in failures['markitdown_errors'].items():
            html_content += f"<li><strong>{error}:</strong> {count} files</li>"
        html_content += "</ul>"
    else:
        html_content += "<p>No MarkItDown errors recorded.</p>"
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    """Main entry point for the analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze results from OCR vs MarkItDown comparison tests"
    )
    
    parser.add_argument(
        '--results-file',
        help='Specific results JSON file to analyze (if not provided, will use latest)'
    )
    
    parser.add_argument(
        '--reports-dir',
        default='comparison_tests/results/reports',
        help='Directory containing results files (default: comparison_tests/results/reports)'
    )
    
    parser.add_argument(
        '--output-html',
        help='Output HTML report file (default: analysis_report.html in reports dir)'
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    # Determine which results file to analyze
    if args.results_file:
        results_file = args.results_file
        if not os.path.exists(results_file):
            logging.error(f"Results file not found: {results_file}")
            sys.exit(1)
    else:
        results_file = find_latest_results(args.reports_dir)
        if not results_file:
            sys.exit(1)
    
    # Load results
    logging.info(f"Loading results from: {results_file}")
    results = load_results_file(results_file)
    
    if not results:
        logging.error("Failed to load results or results file is empty")
        sys.exit(1)
    
    # Perform analysis
    logging.info("Calculating basic statistics...")
    stats = calculate_basic_stats(results)
    
    logging.info("Analyzing results by file type...")
    by_type = analyze_by_file_type(results)
    
    logging.info("Analyzing failure patterns...")
    failures = analyze_failure_patterns(results)
    
    logging.info("Generating recommendations...")
    recommendations = generate_recommendations(stats, by_type, failures)
    
    # Generate HTML report
    if args.output_html:
        output_html = args.output_html
    else:
        output_html = os.path.join(args.reports_dir, 'analysis_report.html')
    
    logging.info(f"Generating HTML report: {output_html}")
    generate_html_report(stats, by_type, failures, recommendations, output_html)
    
    # Print summary to console
    logging.info("\\n" + "="*60)
    logging.info("ANALYSIS SUMMARY")
    logging.info("="*60)
    logging.info(f"Total files analyzed: {stats.get('total_files', 0)}")
    logging.info(f"OCR success rate: {stats.get('ocr_success_rate', 0):.1%}")
    logging.info(f"MarkItDown success rate: {stats.get('markitdown_success_rate', 0):.1%}")
    
    if stats.get('processing_times'):
        ocr_avg = stats['processing_times']['ocr']['average']
        md_avg = stats['processing_times']['markitdown']['average']
        logging.info(f"Average processing time - OCR: {ocr_avg:.2f}s, MarkItDown: {md_avg:.2f}s")
    
    logging.info("\\nRecommendations:")
    for i, rec in enumerate(recommendations, 1):
        logging.info(f"{i}. {rec}")
    
    logging.info(f"\\nDetailed HTML report saved to: {output_html}")


if __name__ == "__main__":
    main()