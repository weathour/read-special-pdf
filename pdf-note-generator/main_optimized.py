import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict
import multiprocessing as mp

# 设置环境变量抑制verbose输出
os.environ['PDFMINER_LOG_LEVEL'] = 'ERROR'

from note_generator import NoteGenerator
from config import load_config, save_config
from file_manager import FileManager
from pdf_processor_optimized import OptimizedPDFProcessor

class OptimizedPDFNoteGenerator:
    """优化的PDF笔记生成器（同步，仅输出结构化 JSON）"""

    def __init__(self, config: Dict, max_workers: int = None):
        self.config = config
        self.file_manager = FileManager()
        self.config_hash = self.file_manager.calculate_config_hash(config)
        self.pdf_processor = OptimizedPDFProcessor(config)
        self.note_generator = NoteGenerator(config)
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'start_time': time.time()
        }

    def process_directory(self, input_dir: Path, output_dir: Path,
                         force_reprocess: bool = False) -> Dict:
        """处理目录中的所有PDF文件"""

        print(f"🔄 扫描PDF文件 | {str(input_dir)}")
        start_time = time.time()
        pdf_files = self._get_all_pdf_files(input_dir)
        end_time = time.time()
        print(f"✅ 扫描PDF文件完成，耗时: {end_time - start_time:.2f} 秒")

        if not pdf_files:
            print(f"❌ 没有找到PDF文件")
            return self.stats

        self.stats['total_files'] = len(pdf_files)

        start_time = time.time()
        self._show_file_distribution(pdf_files, input_dir)
        end_time = time.time()
        print(f"✅ 文件分布显示完成，耗时: {end_time - start_time:.2f} 秒")

        if not force_reprocess:
            start_time = time.time()
            files_to_process = self._filter_files_to_process(pdf_files)
            end_time = time.time()
            print(f"✅ 文件过滤完成，耗时: {end_time - start_time:.2f} 秒")
            self.stats['skipped_files'] = len(pdf_files) - len(files_to_process)
        else:
            files_to_process = pdf_files

        if not files_to_process:
            print(f"ℹ️ 所有文件都已处理过")
            return self.stats

        print(f"ℹ️ 需要处理 {len(files_to_process)} 个文件")
        self._process_files_sequential(files_to_process, output_dir)
        self._show_final_stats()

        return self.stats

    def _get_all_pdf_files(self, directory: Path) -> List[Path]:
        """递归获取所有PDF文件"""
        pdf_files = []
        try:
            for pattern in ['*.pdf', '*.PDF']:
                pdf_files.extend(directory.rglob(pattern))
            pdf_files = sorted(list(set(pdf_files)))
            print(f"ℹ️ 找到 {len(pdf_files)} 个PDF文件")
            return pdf_files
        except Exception as e:
            print(f"❌ 扫描文件时出错: {e}")
            return []

    def _show_file_distribution(self, pdf_files: List[Path], base_dir: Path):
        """显示文件分布"""
        if not pdf_files:
            return
        directories = {}
        total_size = 0
        for pdf_file in pdf_files:
            try:
                rel_path = pdf_file.relative_to(base_dir)
                parent_dir = str(rel_path.parent) if rel_path.parent != Path('.') else '根目录'
                if parent_dir not in directories:
                    directories[parent_dir] = {'count': 0, 'size': 0}
                file_size = pdf_file.stat().st_size
                directories[parent_dir]['count'] += 1
                directories[parent_dir]['size'] += file_size
                total_size += file_size
            except Exception:
                continue
        print(f"ℹ️ 文件分布 (总大小: {self._format_size(total_size)}):")
        for dir_name, info in sorted(directories.items()):
            size_str = self._format_size(info['size'])
            print(f"  📁 {dir_name}: {info['count']} 个文件 ({size_str})")

    def _filter_files_to_process(self, pdf_files: List[Path]) -> List[Path]:
        """过滤需要处理的文件"""
        files_to_process = []
        for pdf_file in pdf_files:
            existing_record = self.file_manager.is_file_processed(pdf_file, self.config_hash)
            if not existing_record:
                files_to_process.append(pdf_file)
            elif existing_record.get('config_changed', False):
                print(f"⚠️ 配置已更改，重新处理: {pdf_file.name}")
                files_to_process.append(pdf_file)
            elif existing_record.get('output_json_path') and not Path(existing_record['output_json_path']).exists():
                print(f"⚠️ 输出文件丢失，重新处理: {pdf_file.name}")
                files_to_process.append(pdf_file)
        return files_to_process

    def _process_files_sequential(self, pdf_files: List[Path], output_dir: Path):
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"🚀 总进度 {i}/{len(pdf_files)} | 处理中: {pdf_file.name}")
            try:
                start_time = time.time()
                self._process_single_file(pdf_file, output_dir)
                end_time = time.time()
                self.stats['processed_files'] += 1
                print(f"✅ 处理完成: {pdf_file.name}，总耗时: {end_time - start_time:.2f} 秒")
            except Exception as e:
                self.stats['failed_files'] += 1
                print(f"❌ 处理失败: {pdf_file.name} - {str(e)}")
                try:
                    self.file_manager.record_processing(
                        pdf_file, self.config_hash,
                        success=False, error_message=str(e)
                    )
                except Exception as db_e:
                    print(f"❗ DB记录处理失败: {db_e}")
                    
    def _process_single_file(self, pdf_file: Path, output_dir: Path):
        txt_dir = output_dir / "txt"
        pdf_dir = output_dir / "pdf"
        txt_dir.mkdir(exist_ok=True)
        pdf_dir.mkdir(exist_ok=True)

        # 1. 提取文本
        start = time.time()
        print(f"🔄 提取文本: {pdf_file.name}")
        text = self.pdf_processor.extract_text(pdf_file)
        if not text or not text.strip():
            raise Exception("无法提取文本内容")
        txt_file_path = txt_dir / f"{pdf_file.stem}.txt"
        with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"✅ 提取的文本已保存到: {txt_file_path}，耗时: {time.time() - start:.2f} 秒")

        # 2. 文本分块
        start = time.time()
        print(f"🔄 文本分块: {pdf_file.name}")
        chunks = self.pdf_processor.chunk_text(text)
        print(f"✅ 文本分块完成，耗时: {time.time() - start:.2f} 秒")

        # 3. 信息提取
        start = time.time()
        print(f"🔄 信息提取: {pdf_file.name}")
        structured_info = self.note_generator.extract_structured_info(chunks)
        print(f"✅ 信息提取完成，耗时: {time.time() - start:.2f} 秒")

        # 4. 保存结构化信息
        start = time.time()
        print(f"🔄 保存结构化信息: {pdf_file.name}")
        self.note_generator.save_structured_info(pdf_file, structured_info, output_dir)
        print(f"✅ 结构化信息保存完成，耗时: {time.time() - start:.2f} 秒")

        # 5. 复制PDF
        start = time.time()
        try:
            pdf_copy_path = pdf_dir / pdf_file.name
            import shutil
            shutil.copy(pdf_file, pdf_copy_path)
            print(f"✅ PDF 文件已复制到: {pdf_copy_path}，耗时: {time.time() - start:.2f} 秒")
        except Exception as e:
            print(f"❌ 复制 PDF 文件失败: {str(e)}")

        processing_time = time.time()
        base_name = pdf_file.stem
        json_files = list((output_dir / "json").glob(f"{base_name}_*.json"))

        self.file_manager.record_processing(
            pdf_file, self.config_hash,
            output_json_path=json_files[-1] if json_files else None,
            processing_time=processing_time,
            success=True
        )

    def _format_size(self, size):
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _show_final_stats(self):
        end_time = time.time()
        total_time = end_time - self.stats['start_time']
        print(f"\n{'='*60}")
        print(f"🎉 处理完成!")
        print(f"📊 处理统计:")
        print(f"   总文件数: {self.stats['total_files']}")
        print(f"   成功处理: {self.stats['processed_files']}")
        print(f"   跳过文件: {self.stats['skipped_files']}")
        print(f"   失败文件: {self.stats['failed_files']}")
        print(f"   成功率: {(self.stats['processed_files'] / self.stats['total_files'] * 100):.1f}%")
        print(f"   总耗时: {total_time:.1f} 秒")

def main():
    parser = argparse.ArgumentParser(description='PDF Paper Structured JSON Extractor (Sync)')
    parser.add_argument('--input-dir', '-i', required=True, help='PDF input directory')
    parser.add_argument('--output-dir', '-o', default='./output', help='Output directory')
    parser.add_argument('--config', '-c', default='./config.json', help='Config file path')
    parser.add_argument('--force', '-f', action='store_true', help='Force re-process all files')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode, less output')
    parser.add_argument('--workers', '-w', type=int, help='Number of workers (not used for async, kept for compatibility)')
    parser.add_argument('--pdf-method', choices=['auto', 'pymupdf', 'pdfplumber', 'pypdf2', 'pdfminer'],
                        default='auto', help='PDF processing method')

    # 管理命令
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    parser.add_argument('--list-history', action='store_true', help='Show processing history')
    parser.add_argument('--cleanup-old', type=int, metavar='DAYS', help='Cleanup failed records older than N days')

    args = parser.parse_args()

    if args.stats or args.list_history or args.cleanup_old:
        file_manager = FileManager()
        if args.stats:
            stats = file_manager.get_statistics()
            print("📊 处理统计:")
            print(f"   总处理数量: {stats['total_processed']}")
            print(f"   成功处理: {stats['successful_processed']}")
            print(f"   失败处理: {stats['failed_processed']}")
            print(f"   成功率: {stats['success_rate']:.1f}%")
            print(f"   总处理时间: {stats['total_time']:.1f}s")
            print(f"   平均处理时间: {stats['avg_time']:.1f}s")
        if args.list_history:
            history = file_manager.get_processing_history(20)
            print("\n📋 最近处理记录:")
            for record in history:
                status = "✅" if record['success'] else "❌"
                print(f"{status} {record['file_name']} - {record['processed_at']}")
        if args.cleanup_old:
            count = file_manager.cleanup_old_records(args.cleanup_old)
            print(f"✅ 清理了 {count} 条失败记录")
        return

    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"❌ 错误：输入目录 {input_path} 不存在")
        sys.exit(1)

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "json").mkdir(exist_ok=True)
    (output_path / "txt").mkdir(exist_ok=True)
    (output_path / "pdf").mkdir(exist_ok=True)

    config = load_config(args.config)
    if args.pdf_method != 'auto':
        config['processing']['pdf_method'] = args.pdf_method
    max_workers = args.workers or min(4, mp.cpu_count())

    processor = OptimizedPDFNoteGenerator(config, max_workers=max_workers)

    try:
        processor.process_directory(
            input_path,
            output_path,
            force_reprocess=args.force
        )
    except KeyboardInterrupt:
        print("\n⏹️  用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()