"""
Unit tests for OpenOCRDocHandler initialization device selection.
"""

import contextlib
import os
import sys
from types import ModuleType
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit.processors.openocr_doc_handler import OpenOCRDocHandler


def _mock_openocr_module(*, fail_gpu: bool = False):
    openocr_mod = ModuleType("openocr")
    openocr_ctor = Mock()

    def _create_pipeline(*args, **kwargs):
        use_gpu = kwargs.get("use_gpu")
        if fail_gpu and use_gpu == "true":
            raise RuntimeError("gpu unavailable")
        return Mock(name=f"pipeline_{use_gpu}")

    openocr_ctor.side_effect = _create_pipeline
    openocr_mod.OpenOCR = openocr_ctor
    return openocr_mod, openocr_ctor


class TestOpenOCRDocHandlerInit:
    """Test device selection behavior during handler initialization."""

    def test_default_uses_gpu(self):
        """Default initialization should request GPU."""
        openocr_mod, openocr_ctor = _mock_openocr_module()
        with (
            patch(
                "ocr_toolkit.processors.openocr_doc_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.openocr_doc_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"openocr": openocr_mod}),
        ):
            handler = OpenOCRDocHandler()

        assert handler.use_gpu is True
        assert openocr_ctor.call_count == 1
        assert openocr_ctor.call_args.kwargs["task"] == "doc"
        assert openocr_ctor.call_args.kwargs["use_gpu"] == "true"
        assert handler.is_available() is True

    def test_use_gpu_false_forces_cpu(self):
        """CPU mode should pass explicit CPU setting to OpenOCR."""
        openocr_mod, openocr_ctor = _mock_openocr_module()
        with (
            patch(
                "ocr_toolkit.processors.openocr_doc_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.openocr_doc_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"openocr": openocr_mod}),
        ):
            handler = OpenOCRDocHandler(use_gpu=False)

        assert handler.use_gpu is False
        assert openocr_ctor.call_count == 1
        assert openocr_ctor.call_args.kwargs["task"] == "doc"
        assert openocr_ctor.call_args.kwargs["use_gpu"] == "false"
        assert handler.is_available() is True

    def test_gpu_failure_falls_back_to_cpu(self):
        """When GPU setup fails, handler should fall back to CPU."""
        openocr_mod, openocr_ctor = _mock_openocr_module(fail_gpu=True)
        with (
            patch(
                "ocr_toolkit.processors.openocr_doc_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.openocr_doc_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"openocr": openocr_mod}),
        ):
            handler = OpenOCRDocHandler(use_gpu=True)

        assert handler.use_gpu is False
        assert openocr_ctor.call_count == 2
        assert openocr_ctor.call_args_list[0].kwargs["use_gpu"] == "true"
        assert openocr_ctor.call_args_list[1].kwargs["use_gpu"] == "false"
        assert handler.is_available() is True

