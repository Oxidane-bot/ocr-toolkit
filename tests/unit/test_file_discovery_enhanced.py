"""
Test cases for enhanced file discovery functionality with recursive search and structure preservation.
"""

import os
import tempfile
import pytest
from pathlib import Path

from ocr_toolkit.utils.file_discovery import discover_files, get_output_file_path


class TestEnhancedFileDiscovery:
    """Test enhanced file discovery features."""

    def test_discover_files_recursive_default(self, tmp_path):
        """Test that recursive search is enabled by default."""
        # Create test directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        # Create test files
        (tmp_path / "file1.pdf").write_text("test1")
        (subdir / "file2.pdf").write_text("test2")
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        assert len(files) == 2
        assert base_dir == str(tmp_path)
        assert str(tmp_path / "file1.pdf") in files
        assert str(subdir / "file2.pdf") in files
        
        # Check relative paths
        assert "file1.pdf" in relative_paths.values()
        assert "subdir/file2.pdf" in relative_paths.values() or "subdir\\file2.pdf" in relative_paths.values()
    
    def test_discover_files_non_recursive(self, tmp_path):
        """Test non-recursive search when explicitly disabled.""" 
        # Create test directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        # Create test files
        (tmp_path / "file1.pdf").write_text("test1")
        (subdir / "file2.pdf").write_text("test2")
        
        files, base_dir, relative_paths = discover_files(str(tmp_path), recursive=False)
        
        assert len(files) == 1
        assert base_dir == str(tmp_path)
        assert str(tmp_path / "file1.pdf") in files
        assert str(subdir / "file2.pdf") not in files
        
        # Check relative paths - should only have top-level file
        assert "file1.pdf" in relative_paths.values()
        assert len(relative_paths) == 1
    
    def test_discover_files_deep_nesting(self, tmp_path):
        """Test recursive discovery with deep directory nesting."""
        # Create nested directory structure
        deep_dir = tmp_path / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)
        
        # Create files at different levels
        (tmp_path / "root.pdf").write_text("root")
        (tmp_path / "level1" / "l1.pdf").write_text("level1")
        (deep_dir / "deep.pdf").write_text("deep")
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        assert len(files) == 3
        assert base_dir == str(tmp_path)
        
        # Verify all files found
        expected_files = {
            str(tmp_path / "root.pdf"),
            str(tmp_path / "level1" / "l1.pdf"), 
            str(deep_dir / "deep.pdf")
        }
        assert set(files) == expected_files
        
        # Check relative paths contain directory structure
        rel_values = set(relative_paths.values())
        assert "root.pdf" in rel_values
        assert any("level1" in path and "l1.pdf" in path for path in rel_values)
        assert any("level3" in path and "deep.pdf" in path for path in rel_values)

    def test_discover_files_single_file(self, tmp_path):
        """Test file discovery for single file input."""
        test_file = tmp_path / "single.pdf"
        test_file.write_text("single file")
        
        files, base_dir, relative_paths = discover_files(str(test_file))
        
        assert len(files) == 1
        assert files[0] == str(test_file)
        assert base_dir == str(tmp_path)
        assert relative_paths[str(test_file)] == "single.pdf"

    def test_get_output_file_path_preserve_structure(self, tmp_path):
        """Test output path generation with structure preservation."""
        input_path = str(tmp_path / "docs" / "section1" / "file.pdf")
        output_dir = str(tmp_path / "output")
        relative_path = "docs/section1/file.pdf"
        
        output_path = get_output_file_path(
            input_path, 
            output_dir, 
            preserve_structure=True, 
            relative_path=relative_path
        )
        
        # Normalize path separators for cross-platform compatibility
        output_path_normalized = output_path.replace('\\', '/')
        expected_path_normalized = str(tmp_path / "output" / "docs" / "section1" / "file.md").replace('\\', '/')
        assert output_path_normalized == expected_path_normalized
    
    def test_get_output_file_path_flat_structure(self, tmp_path):
        """Test output path generation with flat structure."""
        input_path = str(tmp_path / "docs" / "section1" / "file.pdf")
        output_dir = str(tmp_path / "output")
        relative_path = "docs/section1/file.pdf"
        
        output_path = get_output_file_path(
            input_path,
            output_dir,
            preserve_structure=False,
            relative_path=relative_path
        )
        
        expected_path = str(tmp_path / "output" / "file.md")
        assert output_path == expected_path
    
    def test_get_output_file_path_no_relative_path(self, tmp_path):
        """Test output path generation without relative path."""
        input_path = str(tmp_path / "docs" / "file.pdf")
        output_dir = str(tmp_path / "output")
        
        # Should work even without relative_path
        output_path = get_output_file_path(input_path, output_dir)
        
        expected_path = str(tmp_path / "output" / "file.md")
        assert output_path == expected_path

    def test_discover_files_mixed_extensions(self, tmp_path):
        """Test discovery with mixed supported and unsupported extensions."""
        # Create files with different extensions
        (tmp_path / "doc.pdf").write_text("pdf")
        (tmp_path / "image.jpg").write_text("jpg") 
        (tmp_path / "text.txt").write_text("txt")  # Check if .txt is supported
        (tmp_path / "word.docx").write_text("docx")
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        # Should find supported files - let's check what's actually supported
        from ocr_toolkit.utils.file_discovery import get_supported_extensions
        supported_exts = get_supported_extensions()
        
        # Verify only supported files are found
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            assert ext in supported_exts, f"File {file_path} with extension {ext} should not be found"
        
        # Should find at least pdf, jpg, docx if they are supported
        assert len(files) >= 3

    def test_discover_files_real_nested_structure(self):
        """Test file discovery with real nested test structure."""
        # Use the actual nested test structure created in testFile
        test_path = Path(__file__).parent.parent.parent / "testFile" / "nested_test_structure"
        
        # Skip test if nested structure doesn't exist
        if not test_path.exists():
            pytest.skip("Real nested test structure not available")
        
        files, base_dir, relative_paths = discover_files(str(test_path))
        
        # Should find all 7 files in the nested structure
        assert len(files) == 7, f"Expected 7 files, found {len(files)}: {files}"
        assert base_dir == str(test_path)
        
        # Verify expected files exist
        expected_filenames = {
            "instructions for writing 4-1.pdf",  # 2 copies
            "choice question.jpg",  # 2 copies  
            "lesson4.pdf",  # 2 copies
            "discussion 4 instructions.jpg"  # 1 copy
        }
        
        found_filenames = {Path(f).name for f in files}
        for expected in expected_filenames:
            assert expected in found_filenames, f"Missing expected file: {expected}"
        
        # Verify deep nesting is detected (5+ levels)
        deep_files = [f for f in files if "level5" in f]
        assert len(deep_files) >= 1, "Should find files in level5 directory"
        
        # Verify alternative branch is also found
        alt_files = [f for f in files if "alternative_branch" in f]
        assert len(alt_files) >= 2, "Should find files in alternative_branch"
        
        # Check relative paths preserve structure
        for file_path in files:
            rel_path = relative_paths[file_path]
            assert not rel_path.startswith('/') and not rel_path.startswith('\\'), f"Relative path should not be absolute: {rel_path}"
            # Relative path should contain directory structure
            if "level" in file_path:
                assert "level" in rel_path, f"Relative path should preserve directory structure: {rel_path}"

    def test_discover_files_real_nested_non_recursive(self):
        """Test non-recursive discovery with real nested structure."""
        test_path = Path(__file__).parent.parent.parent / "testFile" / "nested_test_structure"
        
        if not test_path.exists():
            pytest.skip("Real nested test structure not available")
        
        files, base_dir, relative_paths = discover_files(str(test_path), recursive=False)
        
        # Should find no files at root level of nested structure
        assert len(files) == 0, f"Non-recursive search should find no files at root level, found: {files}"

    def test_discover_files_boundary_conditions(self, tmp_path):
        """Test boundary conditions for file discovery."""
        # Test with very deep nesting (10 levels)
        deep_path = tmp_path
        for i in range(10):
            deep_path = deep_path / f"level_{i}"
        deep_path.mkdir(parents=True)
        
        # Create file at deepest level
        (deep_path / "deep_file.pdf").write_text("deep")
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        assert len(files) == 1
        assert "level_9" in files[0], "Should find file at level 9"
        
        # Test relative path contains all levels
        rel_path = relative_paths[files[0]]
        levels_in_path = [f"level_{i}" for i in range(10) if f"level_{i}" in rel_path]
        assert len(levels_in_path) == 10, f"All directory levels should be in relative path: {rel_path}"

    def test_discover_files_many_files_per_level(self, tmp_path):
        """Test discovery with multiple files at each directory level."""
        # Create structure with multiple files at each level
        levels = [tmp_path]
        for i in range(5):
            next_level = levels[-1] / f"level{i}"
            next_level.mkdir()
            
            # Create multiple files at each level
            for j in range(3):
                (next_level / f"file_{i}_{j}.pdf").write_text(f"content_{i}_{j}")
            
            levels.append(next_level)
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        # Should find 15 files (3 files × 5 levels)
        assert len(files) == 15, f"Expected 15 files, found {len(files)}"
        
        # Verify files from all levels are found
        for i in range(5):
            # Count files that are directly in level{i} directory (not in subdirectories)
            level_files = [f for f in files if f"level{i}" in f and f"file_{i}_" in f]
            assert len(level_files) == 3, f"Level {i} should have 3 files, found {len(level_files)}: {level_files}"

    def test_discover_files_special_characters_in_paths(self, tmp_path):
        """Test discovery with special characters in directory and file names."""
        # Create directories with special characters (safe for filesystem)
        special_dirs = [
            "dir with spaces",
            "dir-with-dashes", 
            "dir_with_underscores",
            "dir.with.dots"
        ]
        
        file_count = 0
        for dir_name in special_dirs:
            special_dir = tmp_path / dir_name
            special_dir.mkdir()
            
            # Create files with special characters
            special_files = [
                "file with spaces.pdf",
                "file-with-dashes.jpg",
                "file_with_underscores.pdf"
            ]
            
            for file_name in special_files:
                (special_dir / file_name).write_text(f"content for {file_name}")
                file_count += 1
        
        files, base_dir, relative_paths = discover_files(str(tmp_path))
        
        assert len(files) == file_count, f"Expected {file_count} files with special characters"
        
        # Verify relative paths handle special characters correctly
        for file_path in files:
            rel_path = relative_paths[file_path]
            assert rel_path, f"Relative path should not be empty for {file_path}"
            # Should preserve special characters in relative path
            if " " in file_path:
                assert " " in rel_path, f"Spaces should be preserved in relative path: {rel_path}"

    def test_get_output_file_path_deep_nested_structure(self, tmp_path):
        """Test output path generation with deeply nested input structure."""
        # Create deeply nested input path
        deep_input = tmp_path / "docs" / "year2024" / "projects" / "section1" / "subsection" / "document.pdf"
        output_dir = tmp_path / "output"
        relative_path = "docs/year2024/projects/section1/subsection/document.pdf"
        
        # Test with structure preservation
        output_path = get_output_file_path(
            str(deep_input),
            str(output_dir),
            preserve_structure=True,
            relative_path=relative_path
        )
        
        # Should preserve full directory structure in output
        expected_path = str(output_dir / "docs" / "year2024" / "projects" / "section1" / "subsection" / "document.md")
        output_path_normalized = output_path.replace('\\', '/')
        expected_path_normalized = expected_path.replace('\\', '/')
        assert output_path_normalized == expected_path_normalized
        
        # Test without structure preservation  
        flat_output_path = get_output_file_path(
            str(deep_input),
            str(output_dir),
            preserve_structure=False,
            relative_path=relative_path
        )
        
        expected_flat_path = str(output_dir / "document.md")
        assert flat_output_path == expected_flat_path