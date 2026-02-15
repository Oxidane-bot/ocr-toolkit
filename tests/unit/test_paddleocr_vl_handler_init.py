"""
Unit tests for PaddleOCRVLHandler initialization device selection.
"""

import contextlib
import os
import sys
from types import ModuleType
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ocr_toolkit.processors.paddleocr_vl_handler import PaddleOCRVLHandler


def _mock_modules(*, fail_gpu: bool = False):
    paddle_mod = ModuleType("paddle")

    def _set_device(device: str):
        if fail_gpu and device == "gpu":
            raise RuntimeError("gpu unavailable")
        return device

    paddle_mod.set_device = Mock(side_effect=_set_device)

    paddleocr_mod = ModuleType("paddleocr")
    paddleocr_mod.PaddleOCRVL = Mock(return_value=Mock(name="pipeline"))
    return paddle_mod, paddleocr_mod


class TestPaddleOCRVLHandlerInit:
    """Test device selection behavior during handler initialization."""

    def test_default_uses_gpu(self):
        """Default initialization should use GPU."""
        paddle_mod, paddleocr_mod = _mock_modules()
        with (
            patch(
                "ocr_toolkit.processors.paddleocr_vl_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.paddleocr_vl_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"paddle": paddle_mod, "paddleocr": paddleocr_mod}),
        ):
            handler = PaddleOCRVLHandler()

        assert handler.use_gpu is True
        paddle_mod.set_device.assert_called_once_with("gpu")
        paddleocr_mod.PaddleOCRVL.assert_called_once_with(device="gpu:0")
        assert handler.is_available() is True

    def test_use_gpu_false_forces_cpu(self):
        """CPU mode should pass explicit CPU device to PaddleOCRVL."""
        paddle_mod, paddleocr_mod = _mock_modules()
        with (
            patch(
                "ocr_toolkit.processors.paddleocr_vl_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.paddleocr_vl_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"paddle": paddle_mod, "paddleocr": paddleocr_mod}),
        ):
            handler = PaddleOCRVLHandler(use_gpu=False)

        assert handler.use_gpu is False
        paddle_mod.set_device.assert_called_once_with("cpu")
        paddleocr_mod.PaddleOCRVL.assert_called_once_with(device="cpu")
        assert handler.is_available() is True

    def test_gpu_failure_falls_back_to_cpu(self):
        """When GPU setup fails, handler should fall back to CPU."""
        paddle_mod, paddleocr_mod = _mock_modules(fail_gpu=True)
        with (
            patch(
                "ocr_toolkit.processors.paddleocr_vl_handler.suppress_external_library_output",
                side_effect=lambda: contextlib.nullcontext(),
            ),
            patch("ocr_toolkit.processors.paddleocr_vl_handler.setup_nvidia_dll_paths"),
            patch.dict(sys.modules, {"paddle": paddle_mod, "paddleocr": paddleocr_mod}),
        ):
            handler = PaddleOCRVLHandler(use_gpu=True)

        assert handler.use_gpu is False
        assert paddle_mod.set_device.call_count == 2
        assert paddle_mod.set_device.call_args_list[0].args == ("gpu",)
        assert paddle_mod.set_device.call_args_list[1].args == ("cpu",)
        paddleocr_mod.PaddleOCRVL.assert_called_once_with(device="cpu")
        assert handler.is_available() is True
