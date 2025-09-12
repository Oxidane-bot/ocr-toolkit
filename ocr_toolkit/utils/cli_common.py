"""
Common CLI utilities shared across all command-line interfaces.

This module provides shared utilities for CLI modules to reduce code duplication
and maintain consistent behavior across all CLI commands.
"""

import argparse
import logging
from typing import Optional, Dict, Any


def setup_logging() -> None:
    """
    Configure logging for CLI usage.
    
    Sets up a standard logging configuration with timestamp, level, and message
    formatting that is consistent across all CLI commands.
    """
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


class BaseArgumentParser:
    """
    Base argument parser class that provides common CLI argument patterns.
    
    This class centralizes common argument parsing patterns used across
    different CLI commands to ensure consistency and reduce duplication.
    """
    
    @staticmethod
    def create_base_parser(prog: str, description: str, epilog: Optional[str] = None) -> argparse.ArgumentParser:
        """
        Create a base argument parser with standard configuration.
        
        Args:
            prog: Program name for the parser
            description: Description of the command
            epilog: Optional epilog text with examples
            
        Returns:
            Configured ArgumentParser instance
        """
        return argparse.ArgumentParser(
            prog=prog,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog
        )
    
    @staticmethod
    def add_input_path_argument(parser: argparse.ArgumentParser, required: bool = True, 
                               help: str = "Path to document file or directory") -> None:
        """
        Add input path argument to parser.
        
        Args:
            parser: ArgumentParser to add argument to
            required: Whether the argument is required
            help: Help text for the argument
        """
        if required:
            parser.add_argument("input_path", help=help)
        else:
            parser.add_argument("input_path", nargs='?', help=help)
    
    @staticmethod
    def add_workers_argument(parser: argparse.ArgumentParser, default: int = 4) -> None:
        """
        Add workers argument for concurrent processing.
        
        Args:
            parser: ArgumentParser to add argument to
            default: Default number of workers
        """
        parser.add_argument(
            "--workers",
            type=int,
            default=default,
            help=f"Number of concurrent workers for batch processing (default: {default})"
        )
    
    @staticmethod
    def add_verbose_quiet_arguments(parser: argparse.ArgumentParser) -> None:
        """
        Add verbose and quiet logging arguments.
        
        Args:
            parser: ArgumentParser to add arguments to
        """
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )
        parser.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress non-essential output"
        )


def validate_common_arguments(args: argparse.Namespace) -> bool:
    """
    Validate common argument patterns.
    
    Args:
        args: Parsed arguments namespace
        
    Returns:
        True if arguments are valid, False otherwise
    """
    # Check verbose and quiet are not both set
    if hasattr(args, 'verbose') and hasattr(args, 'quiet') and args.verbose and args.quiet:
        print("Error: --verbose and --quiet cannot be used together")
        return False
    
    # Check workers value if present
    if hasattr(args, 'workers') and args.workers is not None:
        if args.workers < 1:
            print("Error: --workers must be at least 1")
            return False
        if args.workers > 16:
            print("Warning: Using more than 16 workers may not improve performance")
    
    return True


def configure_logging_level(args: argparse.Namespace) -> None:
    """
    Configure logging level based on verbose/quiet arguments.
    
    Args:
        args: Parsed arguments with potential verbose/quiet flags
    """
    if hasattr(args, 'quiet') and args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif hasattr(args, 'verbose') and args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


def check_input_path_exists(args: argparse.Namespace) -> bool:
    """
    Check if input path exists and is accessible.
    
    Args:
        args: Parsed arguments with input_path attribute
        
    Returns:
        True if input path exists and is accessible, False otherwise
    """
    import os
    
    if not hasattr(args, 'input_path') or not args.input_path:
        return True  # Skip check if no input_path
    
    if not os.path.exists(args.input_path):
        logging.error(f"Input path does not exist: {args.input_path}")
        return False
    
    return True


def print_processing_summary(total_files: int, successful: int, failed: int, 
                           total_time: float, extra_stats: Optional[Dict[str, Any]] = None) -> None:
    """
    Print a standardized processing summary.
    
    Args:
        total_files: Total number of files processed
        successful: Number of successfully processed files
        failed: Number of failed files
        total_time: Total processing time in seconds
        extra_stats: Optional dictionary of additional statistics to display
    """
    success_rate = (successful / total_files * 100) if total_files > 0 else 0
    
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    print(f"Total files processed: {total_files}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Total time: {total_time:.2f}s")
    
    if extra_stats:
        print("\nAdditional Statistics:")
        for key, value in extra_stats.items():
            print(f"  {key}: {value}")