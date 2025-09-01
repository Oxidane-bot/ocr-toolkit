# refactored_project/ocr_toolkit/common.py
import argparse
import os
import torch
from doctr.models import ocr_predictor
from . import config


def add_common_args(parser):
    """
    Adds common command-line arguments to an argparse parser.

    This function adds standard OCR processing arguments that are used
    across multiple scripts in the toolkit.

    Args:
        parser (argparse.ArgumentParser): The argument parser to add arguments to.

    Returns:
        argparse.ArgumentParser: The parser with added arguments.
    """
    parser.add_argument(
        "--batch_size",
        type=int,
        default=config.DEFAULT_BATCH_SIZE,
        help="Number of pages to process at a time.",
    )
    parser.add_argument(
        "--cpu", action="store_true", help="Force use of CPU even if CUDA is available."
    )
    parser.add_argument(
        "--det-arch",
        type=str,
        default=config.DEFAULT_DET_ARCH,
        help="Detection model architecture to use.",
    )
    parser.add_argument(
        "--reco-arch",
        type=str,
        default=config.DEFAULT_RECO_ARCH,
        help="Recognition model architecture to use.",
    )
    return parser


def load_ocr_model(det_arch, reco_arch, use_cpu=False):
    """
    Loads and returns a doctr OCR predictor model.

    This function creates an OCR predictor with the specified architectures
    and configures it for GPU or CPU usage based on availability and user preference.

    Args:
        det_arch (str): Detection model architecture name (e.g., 'fast_tiny', 'db_resnet50').
        reco_arch (str): Recognition model architecture name (e.g., 'crnn_mobilenet_v3_small').
        use_cpu (bool, optional): Force CPU usage even if CUDA is available. Defaults to False.

    Returns:
        doctr.models.OCRPredictor: The loaded OCR predictor model.

    Example:
        >>> model = load_ocr_model('fast_tiny', 'crnn_mobilenet_v3_small')
        >>> # Process documents with the loaded model
    """
    print(f"Loading model with det_arch='{det_arch}' and reco_arch='{reco_arch}'...")
    use_gpu = not use_cpu and torch.cuda.is_available()

    if use_gpu:
        print("CUDA is available. Using GPU for doctr.")
        model = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True).cuda()
    else:
        print("Using CPU for doctr.")
        model = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True)

    print("Model loaded successfully.")
    return model


def discover_ocr_files(input_path):
    """
    Discovers OCR-supported files from a given path (file or directory).

    This function handles both single file and directory inputs, returning
    a list of files that can be processed by OCR (PDFs, images, Office docs).

    Args:
        input_path (str): Path to a file or directory containing supported files.

    Returns:
        tuple[list[str], str]: A tuple containing:
            - List of supported file paths found
            - Base directory path

    Raises:
        FileNotFoundError: If the input path does not exist.
        ValueError: If input file is not a supported format.

    Example:
        >>> files, base_dir = discover_ocr_files('/path/to/documents/')
        >>> print(f"Found {len(files)} supported files in {base_dir}")
    """
    # Supported file extensions for OCR processing
    supported_extensions = {
        # PDF files
        '.pdf',
        # Image files
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif',
        # Office documents
        '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx'
    }
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    files = []
    base_dir = ""

    if os.path.isdir(input_path):
        print(f"Input is a directory. Searching for supported files in: {input_path}")
        base_dir = input_path
        for filename in sorted(os.listdir(input_path)):
            file_path = os.path.join(input_path, filename)
            if os.path.isfile(file_path):
                ext = os.path.splitext(filename)[1].lower()
                if ext in supported_extensions:
                    files.append(file_path)
        print(f"Found {len(files)} supported files.")
    elif os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in supported_extensions:
            raise ValueError(f"Input file format '{ext}' is not supported. Supported formats: {', '.join(sorted(supported_extensions))}")
        base_dir = os.path.dirname(input_path)
        files.append(input_path)

    if not files:
        print("No supported files found to process.")

    return files, base_dir



def get_output_file_path(input_path, output_dir=None):
    """
    Determines the output file path for a converted Markdown document.

    Args:
        input_path (str): The full path to the input document.
        output_dir (str, optional): The directory to save the output file. 
                                    If None, a default directory is created in the input file's directory.

    Returns:
        str: The full path to the output Markdown file.
    """
    from . import config # Import here to avoid circular dependency if config imports common
    
    input_filename = os.path.basename(input_path)
    output_filename = os.path.splitext(input_filename)[0] + '.md'

    if output_dir:
        output_path = os.path.join(output_dir, output_filename)
    else:
        # If no output_dir is specified, use the default from config
        # inside the input file's directory.
        input_file_dir = os.path.dirname(input_path)
        default_output_dir = os.path.join(input_file_dir, config.DEFAULT_MARKDOWN_OUTPUT_DIR)
        output_path = os.path.join(default_output_dir, output_filename)
        
    return output_path
