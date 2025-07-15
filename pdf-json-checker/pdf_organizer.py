
# pdf_json_checker/pdf_organizer.py
"""
PDF整理器
生成分析报告的同时复制PDF文件到对应目录
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List
import logging
from datetime import datetime

from pdf_manager import PDFManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFOrganizer:
    """PDF整理器 - 分析 + 复制文件"""
    
    def __init__(self, db_path: str = "../papers.db", pdf_base_dir: str = "/home/jia/snap/zotero-snap/common/Zotero/storage"):
        """
        初始化PDF整理器
        Args:
            db_path: papers.db数据库路径
            pdf_base_dir: PDF文件基础目录
        """
        self.pdf_manager = PDFManager(db_path, pdf_base_dir)
        logger.info("🚀 PDF整理器初始化完成")
    
    def organize_and_copy(self, output_dir: str = "./output") -> Dict:
        """
        整理并复制PDF文件
        Args:
            output_dir: 输出目录
        Returns:
            处理结果统计
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📊 开始整理PDF文件到: {output_path}")
        
        # 1. 生成状态报告
        logger.info("📋 生成PDF状态报告...")
        report = self.pdf_manager.generate_status_report()
        
        # 2. 创建子目录
        matched_pdfs_dir = output_path / "matched_pdfs"
        orphaned_pdfs_dir = output_path / "orphaned_pdfs"
        
        matched_pdfs_dir.mkdir(exist_ok=True)
        orphaned_pdfs_dir.mkdir(exist_ok=True)
        
        # 3. 获取各类PDF列表
        missing_pdfs = self.pdf_manager.list_missing_pdfs()
        orphaned_pdfs = self.pdf_manager.list_orphaned_pdfs()
        
        # 4. 保存JSON报告
        self._save_json_reports(output_path, report, missing_pdfs, orphaned_pdfs)
        
        # 5. 复制PDF文件
        copy_stats = self._copy_pdf_files(report, matched_pdfs_dir, orphaned_pdfs_dir)
        
        # 6. 生成汇总报告
        summary = self._generate_summary(copy_stats, missing_pdfs, orphaned_pdfs)
        
        # 7. 保存汇总报告
        self._save_summary_report(output_path, summary)
        
        logger.info("🎉 PDF整理完成!")
        self._print_summary(summary)
        
        return summary
    
    def _save_json_reports(self, output_path: Path, report: Dict, missing_pdfs: List, orphaned_pdfs: List):
        """保存JSON报告文件"""
        logger.info("💾 保存JSON报告文件...")
        
        # 1. 完整状态报告
        self.pdf_manager.save_report(report, output_path / "pdf_status_report.json")
        
        # 2. 缺少PDF的论文列表
        with open(output_path / "missing_pdfs.json", 'w', encoding='utf-8') as f:
            json.dump(missing_pdfs, f, indent=2, ensure_ascii=False)
        
        # 3. 孤立的PDF列表
        with open(output_path / "orphaned_pdfs.json", 'w', encoding='utf-8') as f:
            json.dump(orphaned_pdfs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ JSON报告已保存: {len(missing_pdfs)} 缺失, {len(orphaned_pdfs)} 孤立")
    
    def _copy_pdf_files(self, report: Dict, matched_dir: Path, orphaned_dir: Path) -> Dict:
        """复制PDF文件到对应目录"""
        logger.info("📁 开始复制PDF文件...")
        
        copy_stats = {
            'matched_copied': 0,
            'matched_failed': 0,
            'orphaned_copied': 0,
            'orphaned_failed': 0,
            'matched_files': [],
            'orphaned_files': [],
            'failed_files': []
        }
        
        for status in report['status_list']:
            if status.has_pdf:
                src_path = Path(status.pdf_path)
                
                try:
                    if status.has_json:
                        # 有对应JSON的PDF -> matched_pdfs目录
                        dst_path = matched_dir / src_path.name
                        shutil.copy2(src_path, dst_path)
                        copy_stats['matched_copied'] += 1
                        copy_stats['matched_files'].append({
                            'file_name': src_path.name,
                            'src_path': str(src_path),
                            'dst_path': str(dst_path),
                            'paper_id': status.paper_id
                        })
                        logger.debug(f"  ✅ 复制matched: {src_path.name}")
                        
                    else:
                        # 孤立的PDF -> orphaned_pdfs目录
                        dst_path = orphaned_dir / src_path.name
                        shutil.copy2(src_path, dst_path)
                        copy_stats['orphaned_copied'] += 1
                        copy_stats['orphaned_files'].append({
                            'file_name': src_path.name,
                            'src_path': str(src_path),
                            'dst_path': str(dst_path)
                        })
                        logger.debug(f"  🔍 复制orphaned: {src_path.name}")
                        
                except Exception as e:
                    logger.error(f"❌ 复制失败: {src_path.name} - {e}")
                    if status.has_json:
                        copy_stats['matched_failed'] += 1
                    else:
                        copy_stats['orphaned_failed'] += 1
                    
                    copy_stats['failed_files'].append({
                        'file_name': src_path.name,
                        'src_path': str(src_path),
                        'error': str(e)
                    })
        
        logger.info(f"📁 文件复制完成: matched={copy_stats['matched_copied']}, orphaned={copy_stats['orphaned_copied']}")
        return copy_stats
    
    def _generate_summary(self, copy_stats: Dict, missing_pdfs: List, orphaned_pdfs: List) -> Dict:
        """生成汇总报告"""
        total_papers = len(self.pdf_manager.get_papers_from_db())
        
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_papers_in_db': total_papers,
            'statistics': {
                'matched_pdfs': {
                    'count': copy_stats['matched_copied'],
                    'failed': copy_stats['matched_failed'],
                    'success_rate': copy_stats['matched_copied'] / max(copy_stats['matched_copied'] + copy_stats['matched_failed'], 1) * 100
                },
                'orphaned_pdfs': {
                    'count': copy_stats['orphaned_copied'],
                    'failed': copy_stats['orphaned_failed'],
                    'success_rate': copy_stats['orphaned_copied'] / max(copy_stats['orphaned_copied'] + copy_stats['orphaned_failed'], 1) * 100
                },
                'missing_pdfs': {
                    'count': len(missing_pdfs),
                    'percentage': len(missing_pdfs) / max(total_papers, 1) * 100
                },
                'overall': {
                    'total_pdf_files': copy_stats['matched_copied'] + copy_stats['orphaned_copied'],
                    'match_rate': copy_stats['matched_copied'] / max(total_papers, 1) * 100,
                    'coverage_rate': (copy_stats['matched_copied'] + copy_stats['orphaned_copied']) / max(total_papers, 1) * 100
                }
            },
            'file_details': {
                'matched_files': copy_stats['matched_files'],
                'orphaned_files': copy_stats['orphaned_files'],
                'failed_files': copy_stats['failed_files']
            }
        }
        
        return summary
    
    def _save_summary_report(self, output_path: Path, summary: Dict):
        """保存汇总报告"""
        # 保存详细汇总报告
        with open(output_path / "organization_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # 保存简化的统计报告
        simple_stats = {
            'generated_at': summary['generated_at'],
            'total_papers_in_db': summary['total_papers_in_db'],
            'matched_pdfs_count': summary['statistics']['matched_pdfs']['count'],
            'orphaned_pdfs_count': summary['statistics']['orphaned_pdfs']['count'],
            'missing_pdfs_count': summary['statistics']['missing_pdfs']['count'],
            'match_rate': f"{summary['statistics']['overall']['match_rate']:.1f}%",
            'directories': {
                'matched_pdfs': "./matched_pdfs/",
                'orphaned_pdfs': "./orphaned_pdfs/"
            }
        }
        
        with open(output_path / "simple_statistics.json", 'w', encoding='utf-8') as f:
            json.dump(simple_stats, f, indent=2, ensure_ascii=False)
        
        logger.info("📊 汇总报告已保存")
    
    def _print_summary(self, summary: Dict):
        """打印汇总信息"""
        stats = summary['statistics']
        
        print(f"\n{'='*60}")
        print("📊 PDF整理汇总报告")
        print(f"{'='*60}")
        print(f"🕒 处理时间: {summary['generated_at']}")
        print(f"📚 数据库论文总数: {summary['total_papers_in_db']}")
        print(f"")
        print(f"📁 文件分布:")
        print(f"  ✅ 匹配的PDF: {stats['matched_pdfs']['count']} 个")
        print(f"     → 复制到: ./matched_pdfs/")
        print(f"  🔍 孤立的PDF: {stats['orphaned_pdfs']['count']} 个")
        print(f"     → 复制到: ./orphaned_pdfs/")
        print(f"  ❌ 缺失的PDF: {stats['missing_pdfs']['count']} 个")
        print(f"     → 详见: missing_pdfs.json")
        print(f"")
        print(f"📈 统计指标:")
        print(f"  匹配率: {stats['overall']['match_rate']:.1f}%")
        print(f"  覆盖率: {stats['overall']['coverage_rate']:.1f}%")
        print(f"  总PDF文件: {stats['overall']['total_pdf_files']} 个")
        
        if stats['matched_pdfs']['failed'] > 0 or stats['orphaned_pdfs']['failed'] > 0:
            print(f"")
            print(f"⚠️  复制失败:")
            print(f"  匹配PDF失败: {stats['matched_pdfs']['failed']} 个")
            print(f"  孤立PDF失败: {stats['orphaned_pdfs']['failed']} 个")
        
        print(f"{'='*60}")
    
    def list_files_in_directory(self, output_dir: str = "./output"):
        """列出整理后的文件结构"""
        output_path = Path(output_dir)
        
        if not output_path.exists():
            logger.error(f"输出目录不存在: {output_path}")
            return
        
        print(f"\n📁 整理后的文件结构:")
        print(f"📂 {output_path}/")
        
        # JSON文件
        json_files = list(output_path.glob("*.json"))
        for json_file in sorted(json_files):
            file_size = json_file.stat().st_size / 1024  # KB
            print(f"  📄 {json_file.name} ({file_size:.1f} KB)")
        
        # PDF目录
        for subdir in ['matched_pdfs', 'orphaned_pdfs']:
            subdir_path = output_path / subdir
            if subdir_path.exists():
                pdf_files = list(subdir_path.glob("*.pdf"))
                total_size = sum(f.stat().st_size for f in pdf_files) / 1024 / 1024  # MB
                print(f"  📂 {subdir}/ ({len(pdf_files)} files, {total_size:.1f} MB)")
                
                # 显示前几个文件
                for pdf_file in sorted(pdf_files)[:3]:
                    file_size = pdf_file.stat().st_size / 1024 / 1024  # MB
                    print(f"    📄 {pdf_file.name} ({file_size:.1f} MB)")
                
                if len(pdf_files) > 3:
                    print(f"    ... 还有 {len(pdf_files) - 3} 个文件")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF整理器')
    parser.add_argument('--db-path', default='../papers.db', help='数据库路径')
    parser.add_argument('--pdf-dir', default='../pdfs', help='PDF基础目录')
    parser.add_argument('--output-dir', default='./output', help='输出目录')
    parser.add_argument('--list-files', action='store_true', help='列出整理后的文件')
    
    args = parser.parse_args()
    
    try:
        organizer = PDFOrganizer(args.db_path, args.pdf_dir)
        
        if args.list_files:
            # 只列出文件
            organizer.list_files_in_directory(args.output_dir)
        else:
            # 执行整理
            organizer.organize_and_copy(args.output_dir)
            
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
