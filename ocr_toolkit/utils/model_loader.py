"""
OCR model loading utilities.

This module provides lightweight dependency checks and runtime diagnostics
for OpenOCR-based processing.
"""

import logging
import os
import sys
from contextlib import suppress
from typing import Any

from .runtime_config import configure_ocr_warnings, suppress_external_library_output


def setup_nvidia_dll_paths():
    """
    Add NVIDIA runtime package DLL folders into PATH on Windows.

    This improves compatibility for GPU runtimes installed via pip.
    """
    if sys.platform != "win32":
        return

    logger = logging.getLogger(__name__)
    nvidia_packages = ["nvidia.cudnn", "nvidia.cublas", "nvidia.cuda_runtime", "nvidia.curand"]

    for pkg in nvidia_packages:
        try:
            import importlib.util

            spec = importlib.util.find_spec(pkg)
            if spec and spec.submodule_search_locations:
                package_path = spec.submodule_search_locations[0]
                bin_path = os.path.join(package_path, "bin")

                if os.path.exists(bin_path):
                    os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(bin_path)
                        except Exception as e:
                            logger.debug(f"Failed to add DLL directory {bin_path}: {e}")
        except Exception as e:
            logger.debug(f"Could not locate NVIDIA package {pkg}: {e}")

    try:
        import site

        for site_pkg in site.getsitepackages():
            nvidia_base = os.path.join(site_pkg, "nvidia")
            if not os.path.exists(nvidia_base):
                continue
            for nvidia_pkg in os.listdir(nvidia_base):
                pkg_bin_path = os.path.join(nvidia_base, nvidia_pkg, "bin")
                if os.path.exists(pkg_bin_path):
                    os.environ["PATH"] = pkg_bin_path + os.pathsep + os.environ.get("PATH", "")
                    if hasattr(os, "add_dll_directory"):
                        with suppress(Exception):
                            os.add_dll_directory(pkg_bin_path)
    except Exception as e:
        logger.debug(f"Could not scan site-packages for NVIDIA DLLs: {e}")


def load_ocr_model(use_cpu: bool = False):
    """
    Verify OpenOCR and ONNX Runtime availability for OCR processing.

    OpenOCR handles model download/loading internally. This function performs
    dependency and runtime checks only.

    Args:
        use_cpu: Force CPU mode request.
    """
    setup_nvidia_dll_paths()
    configure_ocr_warnings()

    try:
        with suppress_external_library_output():
            import openocr  # noqa: F401

        openocr_version = getattr(openocr, "__version__", "unknown")
        logging.info(f"OpenOCR version: {openocr_version}")

        with suppress_external_library_output():
            import onnxruntime as ort

        providers = ort.get_available_providers()
        logging.info(f"ONNX Runtime providers: {providers}")

        if use_cpu:
            logging.info("OpenOCR CPU mode requested")
        else:
            if "CUDAExecutionProvider" in providers:
                logging.info("OpenOCR GPU runtime available via CUDAExecutionProvider")
            else:
                logging.warning(
                    "CUDAExecutionProvider not found; OpenOCR will fall back to CPU unless GPU runtime is installed."
                )

        logging.info("OpenOCR installation verified successfully")
        return None
    except ImportError as e:
        raise RuntimeError(
            "OpenOCR is not installed correctly. Install with:\n"
            "  pip install openocr-python\n"
            "For CUDA acceleration, install ONNX Runtime GPU:\n"
            "  pip install onnxruntime-gpu\n"
            f"Import error: {e}"
        ) from e


def get_device_info() -> dict[str, Any]:
    """
    Get runtime information for OpenOCR / ONNX Runtime providers.

    Returns:
        Dictionary with availability and provider diagnostics.
    """
    info: dict[str, Any] = {
        "openocr_available": False,
        "openocr_version": None,
        "onnxruntime_available": False,
        "available_providers": [],
        "cuda_available": False,
    }

    setup_nvidia_dll_paths()
    configure_ocr_warnings()

    try:
        with suppress_external_library_output():
            import openocr

        info["openocr_available"] = True
        info["openocr_version"] = getattr(openocr, "__version__", "unknown")
    except ImportError:
        return info

    try:
        with suppress_external_library_output():
            import onnxruntime as ort

        providers = ort.get_available_providers()
        info["onnxruntime_available"] = True
        info["available_providers"] = providers
        info["cuda_available"] = "CUDAExecutionProvider" in providers
    except ImportError:
        pass

    return info
