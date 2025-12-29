"""
CLI for creating searchable PDF documents.
"""

from __future__ import annotations

import contextlib
import importlib
import logging
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from doctr.io import DocumentFile
from tqdm import tqdm

from .. import config
from ..utils import (
    BaseArgumentParser,
    add_common_ocr_args,
    configure_logging_level,
    discover_pdf_files,
    load_ocr_model,
    setup_logging,
)


def _require_search_dependencies():
    try:
        pikepdf = importlib.import_module("pikepdf")
        hocrtransform = importlib.import_module("ocrmypdf.hocrtransform")
    except ModuleNotFoundError as exc:
        missing = exc.name or "ocrmypdf"
        print(
            f"Missing optional dependency '{missing}' required for `ocr-search`.\n"
            "Install searchable PDF support with one of:\n"
            "  uv pip install \".[search]\"\n"
            "  uv tool install \".[search]\"\n"
            "  pip install \"ocr-cli[search]\"\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    try:
        HocrTransform = hocrtransform.HocrTransform
        HocrTransformError = hocrtransform.HocrTransformError
    except AttributeError as exc:
        print(
            "Installed `ocrmypdf` does not provide `ocrmypdf.hocrtransform`.\n"
            "Reinstall searchable PDF support with one of:\n"
            "  uv pip install --upgrade \".[search]\"\n"
            "  pip install --upgrade \"ocr-cli[search]\"\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    return pikepdf, HocrTransform, HocrTransformError


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def _bbox_from_geometry(geometry, page_dims: tuple[int, int]) -> tuple[int, int, int, int]:
    page_width, page_height = page_dims
    left = int(geometry[0][0] * page_width)
    top = int(geometry[0][1] * page_height)
    right = int(geometry[1][0] * page_width)
    bottom = int(geometry[1][1] * page_height)

    left = _clamp(left, 0, page_width)
    right = _clamp(right, 0, page_width)
    top = _clamp(top, 0, page_height)
    bottom = _clamp(bottom, 0, page_height)

    if right < left:
        left, right = right, left
    if bottom < top:
        top, bottom = bottom, top

    return left, top, right, bottom


def build_hocr(page_result, page_dims: tuple[int, int], *, lang: str | None = None) -> str:
    """Build an hOCR document compatible with ocrmypdf.hocrtransform."""
    root = ET.Element("html")
    body = ET.SubElement(root, "body")

    page_width, page_height = page_dims
    hocr_page = ET.SubElement(body, "div", attrib={"class": "ocr_page"})
    hocr_page.set("title", f"image; bbox 0 0 {page_width} {page_height}")

    for block in page_result.blocks:
        par_attrib = {"class": "ocr_par"}
        if lang:
            par_attrib["lang"] = lang
        hocr_par = ET.SubElement(hocr_page, "p", attrib=par_attrib)

        for line in block.lines:
            left, top, right, bottom = _bbox_from_geometry(line.geometry, page_dims)
            hocr_line = ET.SubElement(
                hocr_par,
                "span",
                attrib={"class": "ocr_line", "title": f"bbox {left} {top} {right} {bottom}"},
            )

            for word in line.words:
                w_left, w_top, w_right, w_bottom = _bbox_from_geometry(word.geometry, page_dims)
                hocr_word = ET.SubElement(
                    hocr_line,
                    "span",
                    attrib={
                        "class": "ocrx_word",
                        "title": f"bbox {w_left} {w_top} {w_right} {w_bottom}",
                    },
                )
                hocr_word.text = word.value

    return ET.tostring(root, encoding="unicode", method="xml")


def _estimate_dpi(pdf_page, page_dims: tuple[int, int]) -> float:
    """Estimate the render DPI used by DocumentFile.from_pdf for this page."""
    page_width_px, page_height_px = page_dims

    try:
        page_width_pt = float(pdf_page.MediaBox[2] - pdf_page.MediaBox[0])
        page_height_pt = float(pdf_page.MediaBox[3] - pdf_page.MediaBox[1])
    except Exception:
        return 300.0

    if page_width_pt <= 0 or page_height_pt <= 0:
        return 300.0

    dpi_x = (page_width_px * 72.0) / page_width_pt
    dpi_y = (page_height_px * 72.0) / page_height_pt
    return (dpi_x + dpi_y) / 2.0


def _pikepdf_save_kwargs(optimize: int, pikepdf) -> dict:
    if optimize <= 0:
        return {"compress_streams": False, "object_stream_mode": pikepdf.ObjectStreamMode.preserve}
    if optimize == 1:
        return {"compress_streams": True, "object_stream_mode": pikepdf.ObjectStreamMode.preserve}
    if optimize == 2:
        return {"compress_streams": True, "object_stream_mode": pikepdf.ObjectStreamMode.generate}
    return {
        "compress_streams": True,
        "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        "recompress_flate": True,
    }


def process_pdf(input_pdf, output_pdf, model, args, *, pikepdf, HocrTransform, HocrTransformError):
    """Processes a single PDF file to make it searchable."""
    logging.info(f"Processing file: {input_pdf} -> {output_pdf}")

    # Create safe temp directory name by removing problematic characters
    safe_name = os.path.basename(input_pdf).replace(" ", "_").replace(".pdf", "")
    temp_dir = f"temp_hocr_{safe_name}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        doc = DocumentFile.from_pdf(input_pdf)
    except Exception as e:
        logging.error(f"Failed to load PDF {input_pdf}: {e}")
        return False

    try:
        if getattr(args, "no_jbig2", False):
            logging.info("Note: --no-jbig2 is ignored (JBIG2 is not used in this pipeline).")

        output_dir = os.path.dirname(output_pdf)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            import torch
            inference_ctx = (
                torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
            )
        except Exception:
            inference_ctx = contextlib.nullcontext()

        lang = "chi_sim" if getattr(args, "zh", False) else None

        with pikepdf.open(input_pdf) as pdf:
            with tqdm(total=len(doc), desc="  - OCR Pages", unit="page") as pbar:
                for batch_start in range(0, len(doc), args.batch_size):
                    batch = doc[batch_start : batch_start + args.batch_size]
                    with inference_ctx:
                        result = model(batch)

                    for offset, (page_img, page_result) in enumerate(
                        zip(batch, result.pages, strict=False)
                    ):
                        page_index = batch_start + offset
                        page_dims = (page_img.shape[1], page_img.shape[0])

                        hocr_content = build_hocr(page_result, page_dims, lang=lang)
                        hocr_path = Path(temp_dir) / f"page_{page_index:04d}.hocr"
                        hocr_path.write_text(hocr_content, encoding="utf-8")

                        text_pdf_path = Path(temp_dir) / f"page_{page_index:04d}.text.pdf"
                        dpi = _estimate_dpi(pdf.pages[page_index], page_dims)
                        try:
                            HocrTransform(hocr_filename=hocr_path, dpi=dpi).to_pdf(
                                out_filename=text_pdf_path,
                                invisible_text=True,
                            )
                        except HocrTransformError as e:
                            logging.error(f"Failed to convert hOCR to PDF text layer: {e}")
                            return False

                        with pikepdf.open(text_pdf_path) as overlay_pdf:
                            pdf.pages[page_index].add_overlay(overlay_pdf.pages[0])

                        pbar.update(1)

            pdf.save(output_pdf, **_pikepdf_save_kwargs(args.optimize, pikepdf))

        logging.info(f"Successfully created searchable PDF: {output_pdf}")
        return True
    except Exception as e:
        logging.error(f"Failed to create searchable PDF for {input_pdf}: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_parser():
    """Create argument parser for search command."""
    parser = BaseArgumentParser.create_base_parser(
        prog="ocr-search",
        description="Create searchable PDFs from scanned PDF documents."
    )

    BaseArgumentParser.add_input_path_argument(
        parser,
        help="Path to PDF file or directory containing PDF files"
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        default=None,
        help="Output path for searchable PDF(s). Optional for directory input."
    )
    parser.add_argument(
        "-O", "--optimize",
        type=int,
        default=1,
        choices=[0, 1, 2, 3],
        help="Set output compression/optimization level (0-3). Default is 1."
    )
    parser.add_argument(
        "--no-jbig2",
        action="store_true",
        help="Deprecated (no effect). Kept for backward compatibility."
    )

    # Add common OCR arguments
    add_common_ocr_args(parser)

    return parser


def main():
    """Main entry point for ocr-search command."""
    setup_logging()

    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging_level(args)

    try:
        pikepdf, HocrTransform, HocrTransformError = _require_search_dependencies()

        # Load OCR model
        model = load_ocr_model(args.det_arch, args.reco_arch, args.cpu)

        # Discover PDF files
        pdf_files, base_dir = discover_pdf_files(args.input_path)
        if not pdf_files:
            logging.error("No PDF files found to process.")
            sys.exit(1)

        # Handle directory vs single file processing
        if os.path.isdir(args.input_path):
            # Directory processing
            output_dir = args.output_path or os.path.join(base_dir, config.DEFAULT_OCR_OUTPUT_DIR)
            logging.info(f"Output will be saved in: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

            success_count = 0
            for i, pdf_file in enumerate(pdf_files):
                logging.info(f"--- Starting file {i+1}/{len(pdf_files)} ---")
                output_file = os.path.join(output_dir, os.path.basename(pdf_file))
                if process_pdf(
                    pdf_file,
                    output_file,
                    model,
                    args,
                    pikepdf=pikepdf,
                    HocrTransform=HocrTransform,
                    HocrTransformError=HocrTransformError,
                ):
                    success_count += 1

            logging.info(f"Directory processing completed! {success_count}/{len(pdf_files)} files processed successfully.")
        else:
            # Single file processing
            if not args.output_path:
                logging.error("Output path must be specified for single file processing.")
                sys.exit(1)

            output_file = args.output_path
            if os.path.isdir(output_file):
                output_file = os.path.join(output_file, os.path.basename(args.input_path))

            if process_pdf(
                args.input_path,
                output_file,
                model,
                args,
                pikepdf=pikepdf,
                HocrTransform=HocrTransform,
                HocrTransformError=HocrTransformError,
            ):
                logging.info("Single file processing completed successfully!")
            else:
                logging.error("Failed to process the file.")
                sys.exit(1)

    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
