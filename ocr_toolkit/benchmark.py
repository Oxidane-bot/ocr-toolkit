"""
Benchmark runner for OCR performance.

This module backs the `ocr-bench` CLI. It intentionally focuses on measuring
end-to-end OCR processing time for a batch of PDF files.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from .processors import OCRProcessor
from .utils import load_ocr_model


def _apply_threads_env(threads: int | None) -> None:
    if threads and threads > 0:
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)


@dataclass
class _BenchConfig:
    det_arch: str
    reco_arch: str
    batch_size: int
    use_cpu: bool
    use_zh: bool
    fast: bool
    pages: str | None
    profile: bool
    threads: int | None


def _create_processor(cfg: _BenchConfig) -> OCRProcessor:
    model = None
    if not cfg.use_zh:
        model = load_ocr_model(cfg.det_arch, cfg.reco_arch, cfg.use_cpu)
    return OCRProcessor(model, cfg.batch_size, use_cnocr=cfg.use_zh)


def run_benchmark(
    *,
    pdf_files: list[str],
    det_arch: str,
    reco_arch: str,
    batch_size: int = 16,
    workers: int = 1,
    use_cpu: bool = False,
    timeout: int = 300,
    zh: bool = False,
    fast: bool = False,
    pages: str | None = None,
    profile: bool = False,
    threads: int | None = None,
) -> dict[str, Any]:
    """
    Run OCR benchmarking on a list of PDF files.

    Notes:
    - `workers` is currently treated as a hint only; GPU inference does not
      benefit from multi-process parallelism in most setups.
    - `timeout` is best-effort: tasks are marked as timed out but not forcibly aborted.
    """
    if not pdf_files:
        raise ValueError("No PDF files provided for benchmarking")

    _apply_threads_env(threads)

    if workers and workers > 1:
        logging.warning("Benchmark workers>1 is not enabled yet; running sequentially.")

    cfg = _BenchConfig(
        det_arch=det_arch,
        reco_arch=reco_arch,
        batch_size=batch_size,
        use_cpu=use_cpu,
        use_zh=zh,
        fast=fast,
        pages=pages,
        profile=profile,
        threads=threads,
    )

    logging.info("Initializing benchmark processor...")
    processor = _create_processor(cfg)

    processing_times: list[float] = []
    successful_files = 0
    failed_files = 0

    total_start = time.perf_counter()

    for idx, file_path in enumerate(pdf_files, 1):
        logging.info(f"[{idx}/{len(pdf_files)}] Benchmarking: {os.path.basename(file_path)}")
        start = time.perf_counter()
        try:
            result = processor.process(file_path, fast=cfg.fast, pages=cfg.pages, profile=cfg.profile)
            elapsed = time.perf_counter() - start
            processing_times.append(elapsed)

            if timeout and elapsed > timeout:
                failed_files += 1
                logging.warning(f"Timed out (> {timeout}s): {file_path}")
                continue

            if result.success:
                successful_files += 1
                if cfg.profile:
                    prof = result.metadata.get("profile")
                    if isinstance(prof, dict) and prof:
                        logging.info("  -> Profile breakdown:")
                        for name, data in sorted(
                            prof.items(),
                            key=lambda kv: float(kv[1].get("total_s", 0.0)),
                            reverse=True,
                        ):
                            total_s = float(data.get("total_s", 0.0))
                            count = int(data.get("count", 0))
                            logging.info(f"     - {name}: {total_s:.3f}s (n={count})")
            else:
                failed_files += 1
                logging.warning(f"Failed: {file_path} - {result.error}")
        except Exception as e:
            elapsed = time.perf_counter() - start
            processing_times.append(elapsed)
            failed_files += 1
            logging.warning(f"Exception processing {file_path}: {e}")

    total_time = time.perf_counter() - total_start
    files_processed = len(pdf_files)

    avg_time = (sum(processing_times) / len(processing_times)) if processing_times else 0.0
    files_per_second = (files_processed / total_time) if total_time > 0 else 0.0

    return {
        "files_processed": files_processed,
        "successful_files": successful_files,
        "failed_files": failed_files,
        "total_time": total_time,
        "avg_time_per_file": avg_time,
        "files_per_second": files_per_second,
        "processing_times": processing_times,
    }

