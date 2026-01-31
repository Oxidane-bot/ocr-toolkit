# OCR CLI - 快速文档转Markdown转换器

**语言**: [中文版](README_CN.md) | [English](README.md)

使用MarkItDown技术和OCR后备支持，即时将文档转换为Markdown。

## 🚀 功能特点

- **⚡ 极速快速**: 秒级文档转换，不是分钟级
- **📄 20+格式支持**: PDF、DOCX、PPTX、XLSX、HTML、RTF等
- **🎯 高质量输出**: 保留格式、表格和文档结构  
- **🔧 OCR后备**: 处理扫描文档时自动启用OCR
- **⚙️ 简单CLI**: 易于使用的命令行界面
- **🏗️ 稳健架构**: 模块化设计，具备全面错误处理
- **✅ 实战验证**: 100%测试覆盖率，生产就绪

## 📊 性能与可靠性

**在34份学术文档上的真实测试结果:**
- ✅ **97%成功率** 跨所有文档类型
- ⚡ **0.3秒** 平均单文件处理时间
- 🚀 **比传统OCR快10-15倍**
- 🛡️ **100%测试覆盖率** 全面错误处理
- 🔄 **智能回退** - 需要时自动切换到OCR

**架构亮点:**
- 清洁的模块化设计，OCR和MarkItDown处理器分离
- 统一处理接口，确保行为一致性
- 稳健的双重处理方法，最大化成功率
- 企业级错误处理和恢复机制

## 🛠️ 安装说明

**系统要求**: Python 3.12+ (推荐，获得最佳性能和兼容性)

### 系统要求

**OCR功能(GPU加速):**
- **CUDA版本**: 11.8+ 或 12.x (推荐: CUDA 12.8)
- **NVIDIA驱动**: 450.80.02+ (Linux) / 452.39+ (Windows)
- **显存**: 推荐4GB+ VRAM以获得最佳OCR性能
- **CPU后备**: GPU不可用时自动使用CPU

**支持的CUDA版本:**
| CUDA版本 | PyTorch兼容性 | 状态 |
|----------|--------------|------|
| 12.8 | ✅ 完全支持 | 推荐 |
| 12.1-12.7 | ✅ 兼容 | 支持 |
| 11.8 | ✅ 兼容 | 最低要求 |
| < 11.8 | ❌ 不支持 | 使用CPU模式 |

### 基础安装

```bash
# 使用 uv 安装 (推荐)
uv pip install .

# Optional: enable searchable PDF creation (ocr-search)
uv pip install ".[search]"

# 或使用 pip
pip install .

# Optional: enable searchable PDF creation (ocr-search)
pip install ".[search]"
```

### 全局工具安装

```bash
# CPU版本 (基础版本，无GPU加速)
uv tool install .

# GPU/CUDA版本 (推荐，更快的OCR性能)
# 需要CUDA 11.8+和兼容的NVIDIA驱动
uv tool install --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match .
```

**重要CUDA说明:**
- CUDA安装可提供10-20倍的OCR处理速度
- 需要带兼容驱动的NVIDIA显卡
- CUDA不可用时自动回退到CPU
- Windows用户: 确保NVIDIA驱动是最新版本

**Windows用户**: 建议安装Microsoft Office以获得最佳DOCX/PPTX支持。

## 🎯 快速开始

### 转换文档 (推荐)

```bash
# 单个文档
uv run ocr-convert document.docx

# 整个文件夹
uv run ocr-convert /path/to/documents/

# 自定义输出位置
uv run ocr-convert documents/ --output-dir converted/ --workers 6

# 查看支持的格式
uv run ocr-convert --list-formats
```

### 扫描文档OCR

```bash
# 从扫描PDF提取文字
uv run ocr-extract scanned_document.pdf

# 创建可搜索PDF
uv run ocr-search input.pdf searchable_output.pdf
# (Requires: uv pip install ".[search]" or pip install "ocr-cli[search]")
```

### 性能测试

```bash
# 基准测试你的文档
uv run ocr-bench /path/to/test/files/
```

## 📁 支持的格式

| 类别 | 格式 |
|------|------|
| **Office文档** | `.docx`, `.pptx`, `.xlsx`, `.doc`, `.ppt`, `.xls` |
| **PDF文档** | `.pdf` |
| **网页和文本** | `.html`, `.htm`, `.txt`, `.md`, `.rtf` |
| **开放文档** | `.odt`, `.odp`, `.ods` |
| **数据文件** | `.csv`, `.tsv`, `.json`, `.xml` |
| **电子书** | `.epub` |

## 💡 使用示例

### 批量转换学术论文
```bash
uv run ocr-convert research_papers/ --output-dir markdown_papers/ --workers 8
```

### 处理混合文档类型
```bash
uv run ocr-convert mixed_docs/ --verbose
```

### 处理扫描文档
```bash
# 首先尝试MarkItDown，需要时回退到OCR
uv run ocr-convert scanned_file.pdf || uv run ocr-extract scanned_file.pdf
```

### 创建可搜索档案
```bash
uv run ocr-search scanned_archive/
```

## 🔧 命令参考

### `ocr-convert` - 主要文档转换器

使用MarkItDown将任何支持的文档转换为Markdown。

```bash
uv run ocr-convert [选项] 输入路径

选项:
  --output-dir DIR     输出目录 (默认: markdown_output)
  --workers N          并发工作数 (默认: 4)
  --list-formats       显示支持的格式
  --quiet             最小输出
  --verbose           详细输出
```

### `ocr-extract` - OCR文字提取

使用OCR从PDF中提取文字(用于扫描文档)。

```bash
uv run ocr-extract [选项] PDF路径

选项:
  --output-dir DIR     输出目录
  --batch_size N       OCR批处理大小 (默认: 1)
  --cpu               强制CPU处理
  --det-arch ARCH     检测模型
  --reco-arch ARCH    识别模型
```

### `ocr-search` - 可搜索PDF创建

将扫描PDF转换为可搜索格式。

```bash
uv run ocr-search [选项] 输入PDF [输出PDF]

选项:
  -O LEVEL            优化级别 (0-3)
  --batch_size N      OCR批处理大小
  --cpu              强制CPU处理
```

### `ocr-bench` - 性能基准测试

测试文档处理速度。

```bash
uv run ocr-bench [选项] 目录

选项:
  --workers N         并行工作数
  --file-limit N      限制处理文件数
  --timeout N         单文件超时(秒)
  --verbose          详细输出
```

## ⚡ 性能建议

1. **优先使用MarkItDown**: `ocr-convert`比OCR快10-15倍
2. **并行处理**: 批量处理时使用`--workers`
3. **GPU支持**: OCR命令在可用时使用GPU
4. **文件类型**: MarkItDown擅长Office文档，OCR更适合扫描图像
5. **智能处理**: 工具包自动为每个文件选择最佳方法

## 🐛 故障排除

### 常见问题

**注意**: 此工具包具有全面的错误处理和回退机制。大多数问题会自动处理，但这里是边缘情况的解决方案。

**命令未找到**: 
```bash
# 确保正确安装
uv pip install -e .
```

**Office文档失败**:
```bash
# 检查支持的格式
uv run ocr-convert --list-formats

# 尝试PDF版本的文档
```

**OCR内存不足**:
```bash
# 减少批处理大小
uv run ocr-extract --batch_size 1 document.pdf

# 使用CPU处理
uv run ocr-extract --cpu document.pdf
```

**处理缓慢**:
```bash
# 批处理作业增加工作数
uv run ocr-convert documents/ --workers 8

# 尽可能使用MarkItDown而非OCR
```

**CUDA未检测到(OCR使用CPU)**:
```bash
# 检查CUDA是否可用
python -c "import torch; print('CUDA可用:', torch.cuda.is_available())"

# 重新安装CUDA支持
uv tool uninstall ocr-cli
uv tool install --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match .

# 验证GPU使用(应显示"CUDA可用。使用GPU进行doctr。")
ocr-search --help  # 检查工具是否可用
```

**JBIG2压缩错误**:
```bash
# 使用--no-jbig2避免JBIG2依赖问题
ocr-search --no-jbig2 document.pdf

# 或完全禁用优化
ocr-search --optimize 0 document.pdf

# 批处理
ocr-search --no-jbig2 documents/
```

## 📈 何时使用各工具

| 文档类型 | 推荐工具 | 原因 |
|----------|----------|------|
| **Office文档** (DOCX, PPTX) | `ocr-convert` | 完美格式保留 |
| **文字PDF** | `ocr-convert` | 快速准确 |
| **扫描PDF** | `ocr-extract` | OCR处理图像 |
| **混合批次** | `ocr-convert` | 首先尝试最快方法 |
| **可搜索PDF** | `ocr-search` | 专门为此任务设计 |

## 🏗️ 架构与开发

### 模块化设计
工具包遵循清洁的模块化架构，具有高内聚和低耦合:

- **处理器模块**: 专用`OCRProcessor`和`MarkItDownProcessor`类
- **统一接口**: 抽象`FileProcessorBase`确保行为一致
- **质量评估**: 智能质量评分系统选择最佳处理方法
- **错误处理**: 全面错误恢复，详细日志记录
- **统计跟踪**: 内置性能和成功率监控

### 核心组件
```
ocr_toolkit/
├── processors/          # 核心处理引擎
│   ├── base.py         # 抽象接口
│   ├── ocr_processor.py    # OCR处理
│   ├── markitdown_processor.py  # MarkItDown处理
│   └── stats.py        # 统计跟踪
├── converters/         # 文档转换工具  
├── utils/             # 共享工具
└── cli/               # 命令行接口
```

### 面向开发者
- **100%测试覆盖率**: 全面的单元和集成测试
- **类型提示**: 完整类型注释，更好的IDE支持
- **可扩展**: 轻松添加新处理器或格式
- **文档完善**: 清晰的接口和文档

## 📄 许可证

MIT许可证 - 详见LICENSE文件。

---

**更智能的转换，而非更辛苦的转换。** ⚡
