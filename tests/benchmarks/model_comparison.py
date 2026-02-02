"""
OCR模型质量对比测试脚本

对比5个不同OCR模型组合的处理质量和性能：
1. 超快速度: fast_tiny + crnn_mobilenet_v3_small (当前baseline)
2. 轻量平衡: fast_small + crnn_mobilenet_v3_large
3. 中等性能: linknet_resnet18 + crnn_vgg16_bn
4. 高质量: db_resnet50 + vitstr_small
5. 最高质量: linknet_resnet50 + parseq

每个模型运行两次以消除首次下载模型的时间影响，使用现有的质量评估系统
"""

import argparse
import gc
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from doctr.io import DocumentFile

from ocr_toolkit import common
from ocr_toolkit.quality_evaluator import QualityEvaluator
from ocr_toolkit.utils import setup_logging_with_file


@dataclass
class ModelConfig:
    """模型配置类"""

    name: str
    det_arch: str
    reco_arch: str
    description: str
    expected_speed: str  # "很快", "快", "中等", "慢", "很慢"


@dataclass
class TestResult:
    """单个测试结果类"""

    model_name: str
    file_path: str
    file_name: str
    file_size: int
    file_extension: str
    run_number: int  # 1 或 2
    success: bool
    processing_time: float
    quality_score: float
    text_length: int
    pages_processed: int
    memory_usage_mb: float
    error_message: str = ""
    quality_details: dict = None


class ModelComparisonTester:
    """OCR模型对比测试器"""

    def __init__(self, output_dir: str = "comparison_results"):
        self.output_dir = output_dir
        self.evaluator = QualityEvaluator()
        self.results: list[TestResult] = []

        # 模型配置
        self.model_configs = [
            ModelConfig(
                name="超快速度",
                det_arch="fast_tiny",
                reco_arch="crnn_mobilenet_v3_small",
                description="当前baseline，最快速度，适合移动端",
                expected_speed="很快",
            ),
            ModelConfig(
                name="轻量平衡",
                det_arch="fast_small",
                reco_arch="crnn_mobilenet_v3_large",
                description="轻量级平衡模型，速度与质量折中",
                expected_speed="快",
            ),
            ModelConfig(
                name="中等性能",
                det_arch="linknet_resnet18",
                reco_arch="crnn_vgg16_bn",
                description="中等性能，平衡质量与速度",
                expected_speed="中等",
            ),
            ModelConfig(
                name="高质量",
                det_arch="db_resnet50",
                reco_arch="vitstr_small",
                description="高质量识别，适合精度要求高的场景",
                expected_speed="慢",
            ),
            ModelConfig(
                name="最高质量",
                det_arch="linknet_resnet50",
                reco_arch="parseq",
                description="最高质量，适合对精度要求极高的场景",
                expected_speed="很慢",
            ),
        ]

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def setup_logging(self):
        """设置日志"""
        log_file = os.path.join(self.output_dir, f"model_comparison_{int(time.time())}.log")
        setup_logging_with_file(log_file, encoding="utf-8")
        logging.info(f"日志文件: {log_file}")

    def get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # 转换为MB
        except:
            return 0.0

    def discover_test_files(self, input_path: str) -> list[str]:
        """发现测试文件"""
        supported_extensions = {
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".doc",
            ".ppt",
            ".xls",
            ".jpg",
            ".jpeg",
            ".png",
        }
        files = []

        if os.path.isfile(input_path):
            if Path(input_path).suffix.lower() in supported_extensions:
                files.append(input_path)
        elif os.path.isdir(input_path):
            for filename in sorted(os.listdir(input_path)):
                filepath = os.path.join(input_path, filename)
                if (
                    os.path.isfile(filepath)
                    and Path(filepath).suffix.lower() in supported_extensions
                ):
                    files.append(filepath)

        logging.info(f"发现 {len(files)} 个测试文件")
        return files

    def process_file_with_model(
        self, file_path: str, model_config: ModelConfig, run_number: int, use_cpu: bool = False
    ) -> TestResult:
        """使用指定模型处理单个文件"""

        result = TestResult(
            model_name=model_config.name,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size=os.path.getsize(file_path),
            file_extension=Path(file_path).suffix.lower(),
            run_number=run_number,
            success=False,
            processing_time=0.0,
            quality_score=0.0,
            text_length=0,
            pages_processed=0,
            memory_usage_mb=0.0,
            quality_details={},
        )

        start_time = time.time()
        memory_before = self.get_memory_usage()

        try:
            # 加载OCR模型
            logging.info(
                f"Run {run_number}: 加载模型 {model_config.name} ({model_config.det_arch} + {model_config.reco_arch})"
            )
            model = common.load_ocr_model(model_config.det_arch, model_config.reco_arch, use_cpu)

            # 处理文件
            if file_path.lower().endswith(".pdf"):
                # PDF文件处理
                doc = DocumentFile.from_pdf(file_path)
                ocr_result = model(doc)
                result.pages_processed = len(doc)

                # 提取文本
                text_content = []
                for page_idx, page in enumerate(ocr_result.pages, 1):
                    page_text = page.render()
                    text_content.append(f"## Page {page_idx}\n\n{page_text}")

                final_text = "\n\n".join(text_content)

            else:
                # 图片文件处理
                doc = DocumentFile.from_images([file_path])
                ocr_result = model(doc)
                result.pages_processed = 1

                # 提取文本
                page_text = ocr_result.pages[0].render()
                final_text = page_text

            # 保存输出文件（只保存第二次运行的结果用于比较）
            if run_number == 2:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                safe_model_name = model_config.name.replace("/", "_")
                output_filename = f"{base_name}_{safe_model_name}.md"
                output_path = os.path.join(self.output_dir, "markdown_outputs", output_filename)

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(final_text)

            # 计算质量评分
            quality_metrics = self.evaluator.calculate_text_quality_score(final_text)
            result.quality_score = quality_metrics["total_score"]
            result.quality_details = quality_metrics
            result.text_length = len(final_text)
            result.success = True

            # 内存使用
            memory_after = self.get_memory_usage()
            result.memory_usage_mb = max(0, memory_after - memory_before)

        except Exception as e:
            result.error_message = str(e)
            logging.error(f"Run {run_number}: 处理失败 {file_path} with {model_config.name}: {e}")

        finally:
            # 清理内存
            try:
                del model
                gc.collect()
            except:
                pass

        result.processing_time = time.time() - start_time
        return result

    def run_comparison_test(self, input_path: str, use_cpu: bool = False) -> dict[str, Any]:
        """运行对比测试"""

        # 发现测试文件
        test_files = self.discover_test_files(input_path)
        if not test_files:
            logging.error("未找到测试文件")
            return {}

        logging.info(
            f"开始模型对比测试，共 {len(test_files)} 个文件，{len(self.model_configs)} 个模型"
        )

        total_tests = len(test_files) * len(self.model_configs) * 2  # 每个模型运行2次
        current_test = 0

        # 对每个文件和模型组合进行测试
        for file_path in test_files:
            logging.info(f"\n=== 测试文件: {os.path.basename(file_path)} ===")

            for model_config in self.model_configs:
                logging.info(f"\n--- 模型: {model_config.name} ---")

                # 运行两次
                for run_number in [1, 2]:
                    current_test += 1
                    logging.info(f"进度: {current_test}/{total_tests} - Run {run_number}/2")

                    result = self.process_file_with_model(
                        file_path, model_config, run_number, use_cpu
                    )

                    self.results.append(result)

                    if result.success:
                        logging.info(
                            f"✓ 成功 - 时间: {result.processing_time:.2f}s, 质量: {result.quality_score:.1f}, 文本长度: {result.text_length}"
                        )
                    else:
                        logging.info(f"✗ 失败 - {result.error_message}")

        # 生成测试报告
        return self.generate_report()

    def generate_report(self) -> dict[str, Any]:
        """生成测试报告"""

        logging.info("\n" + "=" * 80)
        logging.info("OCR模型对比测试报告")
        logging.info("=" * 80)

        # 按模型分组结果（只使用第二次运行的结果，排除模型下载时间）
        model_results = {}

        for result in self.results:
            if result.run_number == 2:  # 只使用第二次运行结果
                model_name = result.model_name
                if model_name not in model_results:
                    model_results[model_name] = []
                model_results[model_name].append(result)

        # 计算每个模型的统计信息
        summary_data = []

        for model_config in self.model_configs:
            model_name = model_config.name
            results = model_results.get(model_name, [])

            if not results:
                continue

            successful_results = [r for r in results if r.success]

            summary = {
                "model_name": model_name,
                "det_arch": model_config.det_arch,
                "reco_arch": model_config.reco_arch,
                "description": model_config.description,
                "expected_speed": model_config.expected_speed,
                "total_files": len(results),
                "successful_files": len(successful_results),
                "success_rate": len(successful_results) / len(results) * 100 if results else 0,
                "avg_processing_time": sum(r.processing_time for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "avg_quality_score": sum(r.quality_score for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "avg_text_length": sum(r.text_length for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "avg_memory_usage": sum(r.memory_usage_mb for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0,
                "total_pages_processed": sum(r.pages_processed for r in successful_results),
            }

            summary_data.append(summary)

        # 按平均处理时间排序
        summary_data.sort(key=lambda x: x["avg_processing_time"])

        # 打印表格报告
        self.print_table_report(summary_data)

        # 保存详细结果
        report_data = {
            "timestamp": int(time.time()),
            "test_type": "ocr_model_comparison",
            "model_configs": [
                {
                    "name": config.name,
                    "det_arch": config.det_arch,
                    "reco_arch": config.reco_arch,
                    "description": config.description,
                    "expected_speed": config.expected_speed,
                }
                for config in self.model_configs
            ],
            "summary": summary_data,
            "detailed_results": [
                {
                    "model_name": r.model_name,
                    "file_name": r.file_name,
                    "file_size": r.file_size,
                    "file_extension": r.file_extension,
                    "run_number": r.run_number,
                    "success": r.success,
                    "processing_time": r.processing_time,
                    "quality_score": r.quality_score,
                    "text_length": r.text_length,
                    "pages_processed": r.pages_processed,
                    "memory_usage_mb": r.memory_usage_mb,
                    "error_message": r.error_message,
                    "quality_details": r.quality_details,
                }
                for r in self.results
            ],
        }

        # 保存JSON报告
        report_file = os.path.join(
            self.output_dir, f"model_comparison_report_{report_data['timestamp']}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logging.info(f"\n详细报告已保存到: {report_file}")

        return report_data

    def print_table_report(self, summary_data: list[dict]):
        """打印表格格式的报告"""

        print("\n" + "=" * 120)
        print("模型性能对比表格")
        print("=" * 120)

        # 表头
        headers = [
            "模型名称",
            "检测+识别架构",
            "成功率",
            "平均时间(s)",
            "质量评分",
            "平均文本长度",
            "内存使用(MB)",
            "适用场景",
        ]

        # 计算列宽
        col_widths = [12, 35, 8, 12, 10, 12, 12, 20]

        # 打印表头
        header_row = "| "
        for i, header in enumerate(headers):
            header_row += f"{header:^{col_widths[i]}} | "
        print(header_row)

        # 分隔线
        separator = "|"
        for width in col_widths:
            separator += "-" * (width + 2) + "|"
        print(separator)

        # 数据行
        for data in summary_data:
            model_name = data["model_name"][:10]
            arch_combo = f"{data['det_arch']}+{data['reco_arch']}"[:33]
            success_rate = f"{data['success_rate']:.1f}%"
            avg_time = f"{data['avg_processing_time']:.2f}"
            quality = f"{data['avg_quality_score']:.1f}"
            text_len = (
                f"{int(data['avg_text_length'] / 1000)}k" if data["avg_text_length"] > 0 else "0"
            )
            memory = f"{data['avg_memory_usage']:.1f}"
            scenario = self._get_scenario_recommendation(data)[:18]

            row = (
                f"| {model_name:^{col_widths[0]}} | {arch_combo:<{col_widths[1]}} | "
                + f"{success_rate:^{col_widths[2]}} | {avg_time:^{col_widths[3]}} | "
                + f"{quality:^{col_widths[4]}} | {text_len:^{col_widths[5]}} | "
                + f"{memory:^{col_widths[6]}} | {scenario:<{col_widths[7]}} |"
            )
            print(row)

        print("=" * 120)

        # 添加建议说明
        print("\n📋 使用建议:")
        print("• 移动端/边缘设备: 选择处理时间最短的模型")
        print("• 日常批量处理: 选择时间和质量平衡的模型")
        print("• 高精度需求: 选择质量评分最高的模型")
        print("• 内存受限环境: 选择内存使用最少的模型")

    def _get_scenario_recommendation(self, data: dict) -> str:
        """根据模型数据推荐使用场景"""
        if data["avg_processing_time"] < 5:
            return "移动端/快速处理"
        elif data["avg_processing_time"] < 15:
            return "日常使用"
        elif data["avg_quality_score"] > 60:
            return "高精度需求"
        else:
            return "特殊用途"


def create_parser() -> argparse.ArgumentParser:
    """创建参数解析器"""
    parser = argparse.ArgumentParser(
        description="OCR模型质量对比测试", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("input_path", help="测试文件路径或包含测试文件的目录")

    parser.add_argument(
        "--output-dir",
        default="model_comparison_results",
        help="结果输出目录 (默认: model_comparison_results)",
    )

    parser.add_argument("--cpu", action="store_true", help="强制使用CPU进行OCR处理")

    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 创建测试器
    tester = ModelComparisonTester(args.output_dir)
    tester.setup_logging()

    logging.info("开始OCR模型质量对比测试")
    logging.info(f"输入路径: {args.input_path}")
    logging.info(f"输出目录: {args.output_dir}")
    logging.info(f"使用CPU: {'是' if args.cpu else '否'}")

    try:
        # 运行对比测试
        results = tester.run_comparison_test(args.input_path, args.cpu)

        if results:
            logging.info("\n🎉 OCR模型对比测试完成!")
        else:
            logging.error("测试失败或无结果")

    except KeyboardInterrupt:
        logging.info("用户中断测试")
        sys.exit(1)
    except Exception as e:
        logging.error(f"测试失败: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
