"""
File tree display utilities for OCR processing.

This module provides utilities for generating and displaying file tree structures
in a visual format, supporting the preserve structure mode of OCR processing.
"""

from pathlib import Path

from .. import config


def generate_file_tree(file_relative_paths: dict[str, str], show_all: bool = True, max_display: int = 15) -> str:
    """
    Generate a visual file tree from relative paths with smart display strategies.

    Args:
        file_relative_paths: Dictionary mapping absolute file paths to relative paths
        show_all: If False, apply smart truncation based on file count
        max_display: Maximum number of files to display when truncating

    Returns:
        Formatted file tree string with Unicode box drawing characters
    """
    if not file_relative_paths:
        return "No files to display"

    total_files = len(file_relative_paths)

    # Smart display strategy based on file count
    if total_files <= config.MAX_TREE_DISPLAY_SMALL:
        # Small count: show everything
        display_mode = "full"
        files_to_show = total_files
    elif total_files <= config.MAX_TREE_DISPLAY_MEDIUM:
        # Medium count: show limited with tree
        display_mode = "limited"
        files_to_show = 12
    else:
        # Large count: show compact summary
        display_mode = "compact"
        files_to_show = 8

    # Override with user preference
    if show_all and total_files <= config.MAX_TREE_DISPLAY_LARGE:
        display_mode = "full"
        files_to_show = total_files
    elif not show_all:
        files_to_show = min(max_display, total_files)

    # Build directory tree structure
    tree = {}

    # Convert relative paths to output paths (.md extension)
    output_paths = []
    for file_count, (_file_path, rel_path) in enumerate(file_relative_paths.items(), start=1):
        if file_count > files_to_show:
            break

        # Convert to .md extension
        rel_path_obj = Path(rel_path)
        output_rel_path = str(rel_path_obj.with_suffix('.md'))
        output_paths.append(output_rel_path)

    # Sort paths for consistent display
    output_paths.sort()

    # Build nested dictionary representing directory structure
    for path in output_paths:
        parts = Path(path).parts
        current = tree

        # Build nested structure
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {}
            if i == len(parts) - 1:
                # Mark as file (leaf node)
                current[part] = None
            else:
                current = current[part]

    # Generate tree display based on mode
    lines = []

    if display_mode == "compact" and total_files > config.MAX_TREE_DISPLAY_MEDIUM:
        # Compact mode: show structure summary
        _build_compact_tree(tree, lines, total_files, files_to_show)
    else:
        # Full or limited mode: show complete tree
        _build_tree_lines(tree, lines, "", True, True)

    # Add truncation notice if needed
    if files_to_show < total_files:
        remaining = total_files - files_to_show
        if display_mode == "compact":
            lines.append(f"... and {remaining} more files in similar structure")
        else:
            lines.append(f"... and {remaining} more files")

    return "\n".join(lines)


def _build_tree_lines(tree_dict: dict, lines: list[str], prefix: str, is_last: bool, is_root: bool = False):
    """
    Recursively build tree lines with Unicode box drawing characters.

    Args:
        tree_dict: Nested dictionary representing directory structure
        lines: List to append formatted lines to
        prefix: Current line prefix for indentation
        is_last: Whether this is the last item at current level
        is_root: Whether this is the root level
    """
    if not tree_dict:
        return

    items = list(tree_dict.items())

    # Separate directories and files, sort each group
    directories = [(k, v) for k, v in items if v is not None]
    files = [(k, v) for k, v in items if v is None]

    directories.sort(key=lambda x: x[0].lower())
    files.sort(key=lambda x: x[0].lower())

    # Combine directories first, then files
    all_items = directories + files

    for i, (name, subtree) in enumerate(all_items):
        is_last_item = (i == len(all_items) - 1)

        if is_root:
            # Root level items
            connector = "└── " if is_last_item else "├── "
            lines.append(f"{connector}{name}")

            if subtree is not None:  # It's a directory
                new_prefix = "    " if is_last_item else "│   "
                _build_tree_lines(subtree, lines, new_prefix, is_last_item)
        else:
            # Non-root items
            connector = "└── " if is_last_item else "├── "
            lines.append(f"{prefix}{connector}{name}")

            if subtree is not None:  # It's a directory
                if is_last_item:
                    new_prefix = prefix + "    "
                else:
                    new_prefix = prefix + "│   "
                _build_tree_lines(subtree, lines, new_prefix, is_last_item)


def _build_compact_tree(tree_dict: dict, lines: list[str], total_files: int, shown_files: int):
    """
    Build a compact tree display for large file counts.

    Shows directory structure with file counts rather than individual files.
    """
    if not tree_dict:
        return

    # Count directories and files at each level
    _analyze_tree_structure(tree_dict)

    lines.append("Output directory structure (sample):")

    # Show top-level directories with file counts
    items = list(tree_dict.items())
    directories = [(k, v) for k, v in items if v is not None]
    files_at_root = [(k, v) for k, v in items if v is None]

    directories.sort(key=lambda x: x[0].lower())

    for i, (dirname, subtree) in enumerate(directories):
        is_last = (i == len(directories) - 1) and len(files_at_root) == 0
        connector = "└── " if is_last else "├── "

        # Count files in this directory tree
        file_count = _count_files_in_tree(subtree)
        lines.append(f"{connector}{dirname}/ ({file_count} files)")

        # Show one level of subdirectories
        if subtree:
            sub_dirs = [(k, v) for k, v in subtree.items() if v is not None]
            if sub_dirs:
                prefix = "    " if is_last else "│   "
                lines.append(f"{prefix}├── ...")

    # Show files at root level if any
    if files_at_root:
        connector = "└── " if not directories else "├── "
        lines.append(f"{connector}({len(files_at_root)} files)")


def _analyze_tree_structure(tree_dict: dict) -> dict[str, int]:
    """Analyze tree structure to get statistics."""
    stats = {"directories": 0, "files": 0, "max_depth": 0}

    def _analyze_recursive(node, depth=0):
        stats["max_depth"] = max(stats["max_depth"], depth)

        for _key, value in node.items():
            if value is None:  # File
                stats["files"] += 1
            else:  # Directory
                stats["directories"] += 1
                _analyze_recursive(value, depth + 1)

    _analyze_recursive(tree_dict)
    return stats


def _count_files_in_tree(tree_dict: dict) -> int:
    """Count total files in a tree structure."""
    if not tree_dict:
        return 0

    count = 0
    for _key, value in tree_dict.items():
        if value is None:  # File
            count += 1
        else:  # Directory
            count += _count_files_in_tree(value)

    return count
