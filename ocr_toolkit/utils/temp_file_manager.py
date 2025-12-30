"""
Temporary file management utilities.

This module centralizes creation and cleanup of temporary files produced during
conversion/OCR. Callers should register any temp paths so they can be cleaned up
reliably, even when exceptions occur.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Iterable


class TempFileManager:
    """Create and clean up temporary files/directories owned by this process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tracked_paths: set[str] = set()
        self._base_dir = Path(tempfile.mkdtemp(prefix="ocr_toolkit_")).resolve()
        atexit.register(self.cleanup_all)

    @property
    def base_dir(self) -> str:
        return str(self._base_dir)

    def create_temp_file(self, *, suffix: str = "", prefix: str = "tmp_", dir: str | None = None) -> str:
        """
        Create a new temporary file and track it for cleanup.

        Returns:
            Path to the created file.
        """
        target_dir = Path(dir).resolve() if dir else self._base_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(target_dir))
        os.close(fd)
        self.add_temp_file(path)
        return path

    def create_temp_dir(self, *, prefix: str = "tmp_", dir: str | None = None) -> str:
        """
        Create a new temporary directory and track it for cleanup.

        Returns:
            Path to the created directory.
        """
        target_dir = Path(dir).resolve() if dir else self._base_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        path = tempfile.mkdtemp(prefix=prefix, dir=str(target_dir))
        self.add_temp_file(path)
        return path

    def add_temp_file(self, path: str) -> None:
        """Register an existing temp path for cleanup."""
        if not path:
            return
        with self._lock:
            self._tracked_paths.add(str(Path(path)))

    def cleanup_file(self, path: str) -> None:
        """Delete a temp file or directory, ignoring errors."""
        if not path:
            return

        normalized = str(Path(path))
        try:
            p = Path(normalized)
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    p.unlink(missing_ok=True)
                except TypeError:
                    if p.exists():
                        p.unlink()
        finally:
            with self._lock:
                self._tracked_paths.discard(normalized)

    def cleanup_all(self) -> None:
        """Best-effort cleanup of all tracked temp paths."""
        with self._lock:
            paths = list(self._tracked_paths)
            self._tracked_paths.clear()

        for path in paths:
            try:
                self.cleanup_file(path)
            except Exception:
                pass

        try:
            shutil.rmtree(self._base_dir, ignore_errors=True)
        except Exception:
            pass


_global_temp_manager: TempFileManager | None = None


def get_temp_manager() -> TempFileManager:
    """Get the global TempFileManager instance."""
    global _global_temp_manager
    if _global_temp_manager is None:
        _global_temp_manager = TempFileManager()
    return _global_temp_manager


def cleanup_temp_files(paths: Iterable[str]) -> None:
    """Convenience helper to delete a list of temp paths."""
    manager = get_temp_manager()
    for path in paths or []:
        manager.cleanup_file(path)

