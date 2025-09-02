#!/usr/bin/env python3
"""
Benchmark OCR performance for Chinese (--zh) on a given PDF by varying parameters
(excluding model). Produces a CSV report.

Usage:
  python scripts/benchmark_zh_params.py INPUT_PDF [OUTPUT_CSV]

Notes:
- Uses wall-clock timing around `ocr-extract`.
- Varies batch size and thread counts via env vars (OMP/MKL).
- Keeps runs modest to avoid long durations.
- Tries to force CnOCR to use GPU via ONNX Runtime CUDA provider when available.
"""

import os
import sys
import time
import csv
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any

BATCH_SIZES = [8, 16, 32]
THREADS = [1, 4, 8]


def run_once(pdf_path: str, batch_size: int, threads: int, output_dir: str) -> Dict[str, Any]:
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["MKL_NUM_THREADS"] = str(threads)
    # Prefer CUDA provider for CnOCR's ONNXRuntime when available
    env.setdefault("CNOCR_ORT_PROVIDERS", "CUDAExecutionProvider,CPUExecutionProvider")
    env.setdefault("CUDA_VISIBLE_DEVICES", "0")

    # Ensure verbose for visibility
    base_cmd = [
        "ocr-extract",
        pdf_path,
        "--ocr-only",
        "--zh",
        "--verbose",
        "--batch-size",
        str(batch_size),
        "--output-dir",
        output_dir,
    ]

    # Try to run via uv with onnxruntime-gpu available; fallback to direct
    cmd: List[str]
    try:
        # Check if uv is present in PATH; if so, prefer a transient with onnxruntime-gpu
        subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        cmd = ["uv", "run", "--with", "onnxruntime-gpu", *base_cmd]
    except Exception:
        cmd = base_cmd

    start = time.perf_counter()
    proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    end = time.perf_counter()
    duration = end - start

    return {
        "batch_size": batch_size,
        "threads": threads,
        "returncode": proc.returncode,
        "wall_time_sec": round(duration, 2),
    }


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/benchmark_zh_params.py INPUT_PDF [OUTPUT_CSV]", file=sys.stderr)
        return 2
    pdf_path = argv[1]
    if not os.path.exists(pdf_path):
        print(f"Input not found: {pdf_path}", file=sys.stderr)
        return 1
    output_csv = argv[2] if len(argv) >= 3 else os.path.join("tests", "benchmarks", "zh_perf_report.csv")

    # Use a temp output dir to avoid cross-run interference
    temp_base = tempfile.mkdtemp(prefix="ocr_bench_out_")

    rows: List[Dict[str, Any]] = []
    try:
        for bs in BATCH_SIZES:
            for th in THREADS:
                run_out_dir = os.path.join(temp_base, f"bs{bs}_th{th}")
                os.makedirs(run_out_dir, exist_ok=True)
                print(f"Running: batch_size={bs}, threads={th} -> {run_out_dir}")
                res = run_once(pdf_path, bs, th, run_out_dir)
                print(f"  -> time={res['wall_time_sec']}s, rc={res['returncode']}")
                rows.append(res)
    finally:
        # Clean temp outputs to not consume disk
        try:
            shutil.rmtree(temp_base, ignore_errors=True)
        except Exception:
            pass

    # Ensure CSV directory exists
    out_dir = os.path.dirname(output_csv) or "."
    os.makedirs(out_dir, exist_ok=True)

    fieldnames = ["batch_size", "threads", "wall_time_sec", "returncode"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print a compact table
    print("\nSpeed report (lower is better):")
    print("batch_size, threads, wall_time_sec")
    for r in rows:
        print(f"{r['batch_size']}, {r['threads']}, {r['wall_time_sec']}")

    print(f"\nSaved CSV: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv)) 