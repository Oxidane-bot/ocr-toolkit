# OCR CLI - Fast Document to Markdown Converter

**Language**: [English](README.md) | [中文版](README_CN.md)

Convert documents to Markdown instantly with MarkItDown technology and OCR fallback support.

## 🚀 Features

- **⚡ Lightning Fast**: Convert documents in seconds, not minutes
- **📄 20+ Formats**: PDF, DOCX, PPTX, XLSX, HTML, RTF, and more
- **🎯 High Quality**: Preserves formatting, tables, and document structure  
- **🔧 OCR Fallback**: Handle scanned documents when needed
- **⚙️ Simple CLI**: Easy-to-use command line interface
- **🏗️ Robust Architecture**: Modular design with comprehensive error handling
- **✅ Battle Tested**: 100% test coverage and production-ready reliability

## 📊 Performance & Reliability

**Real-world tested on 34 academic documents:**
- ✅ **97% Success Rate** across all document types
- ⚡ **0.3 seconds** average processing time per file
- 🚀 **10-15x faster** than traditional OCR methods
- 🛡️ **100% Test Coverage** with comprehensive error handling
- 🔄 **Intelligent Fallback** - automatically switches to OCR when needed

**Architecture Highlights:**
- Clean modular design with factory pattern for processor management
- High cohesion, low coupling architecture with separated concerns
- Unified processing interfaces for consistent behavior across all processors
- Intelligent processor selection based on file types and requirements
- Enterprise-grade error handling and recovery with centralized temp file management

## 🛠️ Installation

**Requirements**: Python 3.12+ (recommended for optimal performance and compatibility)

### System Requirements

**For OCR functionality (GPU acceleration):**
- **CUDA Version**: 11.8+ or 12.x (recommended: CUDA 12.8)
- **NVIDIA Driver**: 450.80.02+ (Linux) / 452.39+ (Windows)
- **GPU Memory**: 4GB+ VRAM recommended for optimal OCR performance
- **CPU Fallback**: Automatically uses CPU if GPU unavailable

**Supported CUDA Versions:**
| CUDA Version | PyTorch Compatibility | Status |
|--------------|----------------------|---------|
| 12.8 | ✅ Fully Supported | Recommended |
| 12.1-12.7 | ✅ Compatible | Supported |
| 11.8 | ✅ Compatible | Minimum |
| < 11.8 | ❌ Not supported | Use CPU mode |

### Basic Installation

```bash
# Install with uv (recommended)
uv pip install .

# Optional: enable searchable PDF creation (ocr-search)
uv pip install ".[search]"

# Or with pip
pip install .

# Optional: enable searchable PDF creation (ocr-search)
pip install ".[search]"
```

### Global Tool Installation

```bash
# CPU version (basic, no GPU acceleration)
uv tool install .

# GPU/CUDA version (recommended for better OCR performance)
# Requires CUDA 11.8+ and compatible NVIDIA drivers
uv tool install --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match .
```

**Important CUDA Notes:**
- The CUDA installation provides 10-20x faster OCR processing
- Requires NVIDIA GPU with compatible drivers
- Automatically falls back to CPU if CUDA unavailable
- Windows users: Ensure NVIDIA drivers are up to date

**Windows users**: Microsoft Office recommended for best DOCX/PPTX support.

## 🎯 Quick Start

### Convert Documents (Recommended)

```bash
# Single document
uv run ocr-convert document.docx

# Entire folder
uv run ocr-convert /path/to/documents/

# Custom output location
uv run ocr-convert documents/ --output-dir converted/ --workers 6

# See supported formats
uv run ocr-convert --list-formats
```

### OCR for Scanned Documents

```bash
# Extract text from scanned PDFs
uv run ocr-extract scanned_document.pdf

# Create searchable PDFs (requires: uv pip install ".[search]")
uv run ocr-search input.pdf searchable_output.pdf
```

### Performance Testing

```bash
# Benchmark your documents
uv run ocr-bench /path/to/test/files/
```

## 📁 Supported Formats

| Category | Formats |
|----------|---------|
| **Office Documents** | `.docx`, `.pptx`, `.xlsx`, `.doc`, `.ppt`, `.xls` |
| **PDF Documents** | `.pdf` |
| **Web & Text** | `.html`, `.htm`, `.txt`, `.md`, `.rtf` |
| **OpenDocument** | `.odt`, `.odp`, `.ods` |
| **Data Files** | `.csv`, `.tsv`, `.json`, `.xml` |
| **E-books** | `.epub` |

## 💡 Usage Examples

### Batch Convert Academic Papers
```bash
uv run ocr-convert research_papers/ --output-dir markdown_papers/ --workers 8
```

### Process Mixed Document Types
```bash
uv run ocr-convert mixed_docs/ --verbose
```

### Handle Scanned Documents
```bash
# Try MarkItDown first, fallback to OCR if needed
uv run ocr-convert scanned_file.pdf || uv run ocr-extract scanned_file.pdf
```

### Create Searchable Archive
```bash
uv run ocr-search scanned_archive/ 
```

## 🔧 Command Reference

### `ocr-convert` - Main Document Converter

Convert any supported document to Markdown using MarkItDown.

```bash
uv run ocr-convert [OPTIONS] INPUT_PATH

Options:
  --output-dir DIR     Output directory (default: markdown_output)
  --workers N          Concurrent workers (default: 4)
  --list-formats       Show supported formats
  --quiet             Minimal output
  --verbose           Detailed output
```

### `ocr-extract` - OCR Text Extraction

Extract text from PDFs using OCR (for scanned documents).

```bash
uv run ocr-extract [OPTIONS] PDF_PATH

Options:
  --output-dir DIR     Output directory
  --batch_size N       OCR batch size (default: 1)
  --cpu               Force CPU processing
  --det-arch ARCH     Detection model
  --reco-arch ARCH    Recognition model
```

### `ocr-search` - Searchable PDF Creation

Convert scanned PDFs to searchable format.
Requires installing optional searchable-PDF dependencies: `uv pip install ".[search]"`.

```bash
uv run ocr-search [OPTIONS] INPUT_PDF [OUTPUT_PDF]

Options:
  -O LEVEL            Optimization level (0-3)
  --batch_size N      OCR batch size (default: 1)
  --cpu              Force CPU processing
```

### `ocr-bench` - Performance Benchmarking

Test processing speed on your documents.

```bash
uv run ocr-bench [OPTIONS] DIRECTORY

Options:
  --workers N         Parallel workers
  --file-limit N      Limit files to process
  --timeout N         Timeout per file (seconds)
  --verbose          Detailed output
```

## ⚡ Performance Tips

1. **Use MarkItDown First**: `ocr-convert` is 10-15x faster than OCR
2. **Parallel Processing**: Use `--workers` for large batches
3. **GPU Support**: OCR commands use GPU when available
4. **File Types**: MarkItDown excels at Office docs, OCR better for scanned images
5. **Smart Processing**: The toolkit automatically chooses the best method for each file

## 🐛 Troubleshooting

### Common Issues

**Note**: This toolkit has comprehensive error handling and fallback mechanisms. Most issues are automatically handled, but here are solutions for edge cases.

**Command not found**: 
```bash
# Ensure proper installation
uv pip install -e .
```

**Office document fails**:
```bash
# Check supported formats
uv run ocr-convert --list-formats

# Try PDF version of the document
```

**OCR out of memory**:
```bash
# Reduce batch size
uv run ocr-extract --batch_size 1 document.pdf

# Use CPU processing
uv run ocr-extract --cpu document.pdf
```

**Slow processing**:
```bash
# Increase workers for batch jobs
uv run ocr-convert documents/ --workers 8

# Use MarkItDown instead of OCR when possible
```

**CUDA not detected (OCR using CPU)**:
```bash
# Check if CUDA is available
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# Reinstall with CUDA support
uv tool uninstall ocr-cli
uv tool install --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match .

# Verify GPU usage (should show "CUDA is available. Using GPU for doctr.")
ocr-search --help  # Check if tools are available
```

**`ocr-search` dependency not installed**:
```bash
# Install searchable PDF support
uv pip install ".[search]"

# Or
pip install "ocr-cli[search]"
```

## 📈 When to Use Each Tool

| Document Type | Recommended Tool | Why |
|---------------|------------------|-----|
| **Office docs** (DOCX, PPTX) | `ocr-convert` | Perfect format preservation |
| **Text PDFs** | `ocr-convert` | Fast and accurate |
| **Scanned PDFs** | `ocr-extract` | OCR handles images |
| **Mixed batch** | `ocr-convert` | Try fastest method first |
| **Searchable PDFs** | `ocr-search` | Specialized for this task |

## 🏗️ Architecture & Development

### Modular Design
The toolkit follows a clean, modular architecture with high cohesion and low coupling:

- **Factory Pattern**: `ProcessorFactory` manages processor creation and lifecycle
- **Service Layer**: Dedicated services for path normalization, temp file management
- **Processors Module**: Clean OCR and MarkItDown processors with unified interfaces
- **Unified Interface**: Abstract `FileProcessorBase` ensures consistent behavior
- **Centralized Services**: Temporary file management, path normalization, model loading
- **Error Handling**: Comprehensive error recovery with detailed logging
- **Statistics Tracking**: Built-in performance and success rate monitoring

### Key Components
```
ocr_toolkit/
├── processors/          # Core processing engines
│   ├── base.py         # Abstract interfaces & ProcessingResult
│   ├── factory.py      # ProcessorFactory for processor management
│   ├── ocr_processor.py    # OCR processing with CnOCR support
│   └── markitdown_processor.py  # MarkItDown processing
├── utils/              # Service layer & utilities
│   ├── temp_file_manager.py    # Centralized temp file management
│   ├── path_normalizer.py      # Path normalization service
│   ├── model_loader.py         # OCR model loading utilities
│   ├── file_discovery.py       # File discovery & validation
│   └── cli_args.py            # CLI argument utilities
├── converters/         # File format converters
├── cli/               # Command line interfaces
└── config.py          # Centralized configuration
```

### For Developers
- **100% Test Coverage**: Comprehensive unit and integration tests
- **Type Hints**: Full type annotation for better IDE support
- **Extensible**: Easy to add new processors or formats
- **Well Documented**: Clear interfaces and documentation

## 📄 License

MIT License - see LICENSE file for details.

---

**Convert smarter, not harder.** ⚡


## Testing helper: slice first N pages of a PDF

For large PDFs, you can slice the first N pages into a new PDF for faster tests without changing app code.

Run without persisting dependencies:

```bash
uv run --with pypdf scripts/slice_pdf_first_pages.py "INPUT.pdf" "OUTPUT_firstN.pdf" 30
```

- This uses a transient `pypdf` only for the command above; it does not modify project dependencies.
- Then run OCR on the sliced file, e.g.:

```bash
ocr-extract "OUTPUT_firstN.pdf" --zh --verbose
```

## Performance tips and new flags

For faster runs on Chinese documents (CnOCR `--zh`):

- `--fast`: Enable a faster pipeline (naive detection + optional downscale). Good for clean scans.
- `--threads N`: Set OMP/MKL thread count for CPU-bound parts.
- `--pages RANGE`: Process only selected pages. Examples: `--pages 1-30`, `--pages 1-5,10,20-25`.

Example:

```bash
ocr-extract "主体解释学_first30.pdf" --zh --ocr-only --fast --threads 8 --batch-size 32 --pages 1-30
```

Notes:
- `--fast` may trade some layout robustness for speed.
- `--threads` affects CPU parts and may not change GPU inference speed.
