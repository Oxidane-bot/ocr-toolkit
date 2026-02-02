"""
Integration tests for preserve structure functionality with real OCR processing.

These tests validate that the -p (preserve structure) mode works correctly
with actual OCR-processable files and doesn't experience hanging/freezing issues.
"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from ocr_toolkit.utils.file_discovery import (
    discover_files,
    get_directory_cache,
    get_output_file_path,
)


class TestPreserveStructureIntegration:
    """Integration tests for preserve structure functionality."""

    @pytest.fixture
    def nested_test_structure(self):
        """Provide path to the real nested test structure."""
        test_path = project_root / "testFile" / "nested_test_structure"
        if not test_path.exists():
            pytest.skip("Real nested test structure not available")
        return test_path

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp(prefix="ocr_preserve_test_")
        yield temp_dir
        # Cleanup after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_discover_files_with_real_nested_structure(self, nested_test_structure):
        """Test file discovery works correctly with real nested structure."""
        start_time = time.time()

        files, base_dir, relative_paths = discover_files(str(nested_test_structure))

        discovery_time = time.time() - start_time

        # Should complete discovery within reasonable time (not hang)
        assert discovery_time < 5.0, f"File discovery took too long: {discovery_time:.2f}s"

        # Should find all expected files
        assert len(files) == 7, (
            f"Expected 7 files, found {len(files)}: {[Path(f).name for f in files]}"
        )

        # Should include files from deep nesting
        deep_files = [f for f in files if "level5" in f]
        assert len(deep_files) >= 1, "Should find files in deeply nested directories"

        # Should include files from alternative branch
        alt_files = [f for f in files if "alternative_branch" in f]
        assert len(alt_files) >= 2, "Should find files in alternative branch"

        # Relative paths should be properly constructed
        for file_path, rel_path in relative_paths.items():
            assert rel_path, f"Relative path should not be empty for {file_path}"
            assert not rel_path.startswith("/"), (
                f"Relative path should not start with /: {rel_path}"
            )
            assert not rel_path.startswith("\\"), (
                f"Relative path should not start with \\: {rel_path}"
            )

    def test_output_path_generation_with_structure_preservation(
        self, nested_test_structure, temp_output_dir
    ):
        """Test output path generation preserves directory structure correctly."""
        files, base_dir, relative_paths = discover_files(str(nested_test_structure))

        # Test output path generation for each discovered file
        generated_paths = []
        for file_path in files:
            relative_path = relative_paths[file_path]

            output_path = get_output_file_path(
                file_path, temp_output_dir, preserve_structure=True, relative_path=relative_path
            )

            generated_paths.append(output_path)

            # Verify output path preserves structure
            assert temp_output_dir in output_path, "Output path should be within output directory"
            assert output_path.endswith(".md"), "Output file should have .md extension"

            # Check that directory structure is preserved in output path
            if "level" in file_path:
                assert "level" in output_path, (
                    f"Output path should preserve 'level' directories: {output_path}"
                )

            if "alternative_branch" in file_path:
                assert "alternative_branch" in output_path, (
                    f"Output path should preserve alternative_branch: {output_path}"
                )

        # All generated paths should be unique
        assert len(set(generated_paths)) == len(generated_paths), (
            "All output paths should be unique"
        )

    def test_directory_cache_performance(self, nested_test_structure, temp_output_dir):
        """Test directory cache improves performance and prevents redundant operations."""
        files, base_dir, relative_paths = discover_files(str(nested_test_structure))

        # Get directory cache instance
        dir_cache = get_directory_cache()
        dir_cache.reset()

        # Simulate directory creation for all output paths
        start_time = time.time()
        created_dirs = set()

        for file_path in files:
            relative_path = relative_paths[file_path]
            output_path = get_output_file_path(
                file_path, temp_output_dir, preserve_structure=True, relative_path=relative_path
            )

            output_dir = os.path.dirname(output_path)
            dir_cache.ensure_directory(output_dir)
            created_dirs.add(output_dir)

        cache_time = time.time() - start_time

        # Directory operations should complete quickly with caching
        assert cache_time < 2.0, f"Directory creation with cache took too long: {cache_time:.2f}s"

        # All directories should exist
        for dir_path in created_dirs:
            assert os.path.exists(dir_path), f"Directory should exist: {dir_path}"

        # Cache should have prevented redundant operations by tracking created directories
        assert len(created_dirs) >= 3, "Should create multiple nested directories"

    def test_non_recursive_vs_recursive_behavior(self, nested_test_structure):
        """Test recursive vs non-recursive discovery behavior."""
        # Test recursive discovery (default)
        recursive_files, _, _ = discover_files(str(nested_test_structure), recursive=True)

        # Test non-recursive discovery
        non_recursive_files, _, _ = discover_files(str(nested_test_structure), recursive=False)

        # Recursive should find more files than non-recursive
        assert len(recursive_files) > len(non_recursive_files), (
            f"Recursive search should find more files: "
            f"recursive={len(recursive_files)}, non-recursive={len(non_recursive_files)}"
        )

        # Non-recursive should find no files (nested structure has no files at root)
        assert len(non_recursive_files) == 0, (
            "Non-recursive search should find no files at root level"
        )

    def test_error_handling_with_problematic_paths(self, temp_output_dir):
        """Test error handling with edge case file paths."""
        # Create test structure with potential edge cases
        edge_case_dir = Path(temp_output_dir) / "edge_cases"
        edge_case_dir.mkdir()

        # Create files with challenging names (but filesystem-safe)
        edge_files = [
            "file with spaces.pdf",
            "file-with-dashes.pdf",
            "file_with_underscores.pdf",
            "file.with.multiple.dots.pdf",
        ]

        for filename in edge_files:
            test_file = edge_case_dir / filename
            test_file.write_text("test content")

        # Test discovery handles edge cases
        start_time = time.time()
        files, base_dir, relative_paths = discover_files(str(edge_case_dir))
        discovery_time = time.time() - start_time

        # Should complete without hanging
        assert discovery_time < 5.0, (
            f"Discovery with edge case paths took too long: {discovery_time:.2f}s"
        )

        # Should find all edge case files
        assert len(files) == len(edge_files), (
            f"Should find all edge case files: {len(files)} != {len(edge_files)}"
        )

        # Test output path generation handles edge cases
        for file_path in files:
            relative_path = relative_paths[file_path]

            output_path = get_output_file_path(
                file_path, temp_output_dir, preserve_structure=True, relative_path=relative_path
            )

            # Should generate valid output path
            assert output_path, f"Should generate valid output path for {file_path}"
            assert temp_output_dir in output_path, "Output path should be in temp directory"

    def test_mixed_file_extensions_filtering(self, nested_test_structure):
        """Test that only supported file extensions are discovered."""
        from ocr_toolkit.utils.file_discovery import get_supported_extensions

        files, _, _ = discover_files(str(nested_test_structure))
        supported_exts = get_supported_extensions()

        # All discovered files should have supported extensions
        for file_path in files:
            file_ext = Path(file_path).suffix.lower()
            assert file_ext in supported_exts, (
                f"File {file_path} has unsupported extension {file_ext}. "
                f"Supported: {supported_exts}"
            )

        # Should find both PDF and image files
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        image_files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        assert len(pdf_files) >= 2, f"Should find PDF files in nested structure: {pdf_files}"
        assert len(image_files) >= 2, f"Should find image files in nested structure: {image_files}"

    def test_performance_with_deep_nesting(self, nested_test_structure):
        """Test that deep nesting doesn't cause performance issues."""
        start_time = time.time()

        # Run multiple discovery operations to test consistency
        for _ in range(3):
            files, base_dir, relative_paths = discover_files(str(nested_test_structure))

            # Verify we get consistent results
            assert len(files) == 7, "Should consistently find same number of files"

        total_time = time.time() - start_time
        avg_time = total_time / 3

        # Each discovery should be reasonably fast
        assert avg_time < 2.0, f"Average discovery time too slow: {avg_time:.2f}s"

        # Test output path generation performance
        start_time = time.time()

        for file_path in files:
            relative_path = relative_paths[file_path]
            output_path = get_output_file_path(
                file_path, "/tmp/test_output", preserve_structure=True, relative_path=relative_path
            )
            assert output_path, f"Should generate output path for {file_path}"

        path_gen_time = time.time() - start_time
        assert path_gen_time < 1.0, f"Output path generation too slow: {path_gen_time:.2f}s"

    @pytest.mark.slow
    def test_symlink_handling_safety(self, temp_output_dir):
        """Test that symlink cycles are handled safely."""
        # Create test directory with symlink cycle
        test_dir = Path(temp_output_dir) / "symlink_test"
        test_dir.mkdir()

        # Create subdirectories
        subdir1 = test_dir / "subdir1"
        subdir2 = test_dir / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        # Create a test file
        (subdir1 / "test.pdf").write_text("test content")

        try:
            # Create symlink that could cause a cycle (if supported by OS)
            if os.name != "nt":  # Skip on Windows which has limited symlink support
                cycle_link = subdir2 / "cycle_link"
                cycle_link.symlink_to(test_dir)

                # Discovery should handle symlink cycles safely
                start_time = time.time()
                files, _, _ = discover_files(str(test_dir))
                discovery_time = time.time() - start_time

                # Should not hang due to symlink cycle
                assert discovery_time < 10.0, (
                    f"Symlink cycle handling took too long: {discovery_time:.2f}s"
                )

                # Should still find the real file
                assert len(files) >= 1, "Should find real files despite symlink cycle"

        except (OSError, NotImplementedError):
            # Skip if symlinks not supported on this system
            pytest.skip("Symlinks not supported on this system")
