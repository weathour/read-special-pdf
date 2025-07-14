
# pdf_json_checker/pdf_manager.py
"""
PDF筛选与管理模块
基于papers.db数据库进行PDF文件管理
"""

import sqlite3
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import logging
from datetime import datetime
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PDFStatus:
    """PDF状态信息"""
    file_name: str
    has_json: bool
    has_pdf: bool
    json_path: Optional[str] = None
    pdf_path: Optional[str] = None
    paper_id: Optional[int] = None

class PDFManager:
    """PDF文件管理器"""
    
    def __init__(self, db_path: str = "../papers.db", pdf_base_dir: str = "../pdfs"):
        """
        初始化PDF管理器
        Args:
            db_path: papers.db数据库路径
            pdf_base_dir: PDF文件基础目录
        """
        self.db_path = Path(db_path).resolve()
        self.pdf_base_dir = Path(pdf_base_dir).resolve()
        
        # 创建PDF目录结构
        self.pdf_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证数据库连接
        self._verify_database()
        
        logger.info(f"✅ PDF管理器初始化完成")
        logger.info(f"📁 数据库路径: {self.db_path}")
        logger.info(f"📁 PDF目录: {self.pdf_base_dir}")
    
    def _verify_database(self):
        """验证数据库连接"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM papers")
            count = cursor.fetchone()[0]
            conn.close()
            logger.info(f"📊 数据库连接成功，共有 {count} 篇论文")
        except Exception as e:
            raise Exception(f"数据库连接失败: {e}")
    
    def get_papers_from_db(self) -> List[Dict]:
        """从数据库获取所有论文信息"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, file_name, title_cn, title_en, authors, 
                   publication_year, venue, json_path, created_at
            FROM papers
            ORDER BY id
        ''')
        
        papers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"📚 从数据库获取 {len(papers)} 篇论文")
        return papers
    
    def scan_pdf_directory(self, scan_subdirs: bool = True) -> List[Path]:
        """扫描PDF目录，获取所有PDF文件"""
        pdf_files = []
        
        if scan_subdirs:
            # 递归扫描子目录
            pdf_files = list(self.pdf_base_dir.rglob("*.pdf"))
        else:
            # 只扫描根目录
            pdf_files = list(self.pdf_base_dir.glob("*.pdf"))
        
        logger.info(f"🔍 扫描到 {len(pdf_files)} 个PDF文件")
        return pdf_files
    
    def extract_basename(self, file_path: str) -> str:
        """提取文件基础名（去除扩展名）"""
        return Path(file_path).stem
    
    def find_pdf_for_paper(self, paper: Dict) -> Optional[Path]:
        """为数据库中的论文查找对应的PDF文件"""
        file_name = paper.get('file_name', '')
        if not file_name:
            return None
        
        # 提取基础文件名
        base_name = self.extract_basename(file_name)
        
        # 可能的PDF文件名模式
        possible_names = [
            f"{base_name}.pdf",
            f"{file_name}.pdf" if not file_name.endswith('.pdf') else file_name,
            f"{base_name}_original.pdf",
            f"{base_name}_processed.pdf"
        ]
        
        # 在PDF目录中搜索
        for pdf_file in self.scan_pdf_directory():
            if pdf_file.name in possible_names:
                return pdf_file
            
            # 模糊匹配（去除特殊字符后比较）
            pdf_base = self.normalize_filename(pdf_file.stem)
            paper_base = self.normalize_filename(base_name)
            
            if pdf_base == paper_base:
                return pdf_file
        
        return None
    
    def normalize_filename(self, filename: str) -> str:
        """标准化文件名，用于模糊匹配"""
        import re
        # 移除特殊字符，转小写
        normalized = re.sub(r'[^\w\s-]', '', filename.lower())
        # 移除多余空格和下划线
        normalized = re.sub(r'[\s_-]+', '', normalized)
        return normalized.strip()
    
    def find_json_for_pdf(self, pdf_path: Path, papers: List[Dict]) -> Optional[Dict]:
        """为PDF文件查找对应的JSON记录"""
        pdf_base = self.normalize_filename(pdf_path.stem)
        
        for paper in papers:
            file_name = paper.get('file_name', '')
            if not file_name:
                continue
            
            # 标准化比较
            paper_base = self.normalize_filename(self.extract_basename(file_name))
            
            if pdf_base == paper_base:
                return paper
        
        return None
    
    def generate_status_report(self) -> Dict:
        """生成PDF状态报告"""
        logger.info("🔍 开始生成PDF状态报告...")
        
        # 获取数据库中的论文
        papers = self.get_papers_from_db()
        
        # 扫描PDF文件
        pdf_files = self.scan_pdf_directory()
        
        # 分析状态
        status_list = []
        
        # 1. 检查每篇论文的PDF状态
        logger.info("📊 检查论文的PDF状态...")
        for paper in papers:
            pdf_path = self.find_pdf_for_paper(paper)
            
            status = PDFStatus(
                file_name=paper.get('file_name', ''),
                has_json=True,  # 数据库中的都有JSON
                has_pdf=pdf_path is not None,
                json_path=paper.get('json_path', ''),
                pdf_path=str(pdf_path) if pdf_path else None,
                paper_id=paper.get('id')
            )
            status_list.append(status)
        
        # 2. 检查孤立的PDF文件（没有对应JSON的）
        logger.info("🔍 检查孤立的PDF文件...")
        matched_pdfs = {status.pdf_path for status in status_list if status.has_pdf}
        
        for pdf_file in pdf_files:
            if str(pdf_file) not in matched_pdfs:
                status = PDFStatus(
                    file_name=pdf_file.name,
                    has_json=False,
                    has_pdf=True,
                    pdf_path=str(pdf_file)
                )
                status_list.append(status)
        
        # 生成统计信息
        stats = {
            'total_papers_in_db': len(papers),
            'total_pdf_files': len(pdf_files),
            'papers_with_pdf': sum(1 for s in status_list if s.has_json and s.has_pdf),
            'papers_without_pdf': sum(1 for s in status_list if s.has_json and not s.has_pdf),
            'orphaned_pdfs': sum(1 for s in status_list if not s.has_json and s.has_pdf),
            'match_rate': 0.0
        }
        
        if stats['total_papers_in_db'] > 0:
            stats['match_rate'] = stats['papers_with_pdf'] / stats['total_papers_in_db'] * 100
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'status_list': status_list,
            'pdf_directory': str(self.pdf_base_dir),
            'database_path': str(self.db_path)
        }
        
        logger.info("✅ PDF状态报告生成完成")
        self._print_status_summary(stats)
        
        return report
    
    def _print_status_summary(self, stats: Dict):
        """打印状态摘要"""
        print("\n" + "="*60)
        print("📊 PDF文件状态统计")
        print("="*60)
        print(f"📚 数据库中论文总数: {stats['total_papers_in_db']}")
        print(f"📄 PDF文件总数: {stats['total_pdf_files']}")
        print(f"✅ 有对应PDF的论文: {stats['papers_with_pdf']}")
        print(f"❌ 缺少PDF的论文: {stats['papers_without_pdf']}")
        print(f"🔍 孤立的PDF文件: {stats['orphaned_pdfs']}")
        print(f"📈 匹配率: {stats['match_rate']:.1f}%")
        print("="*60)
    
    def list_missing_pdfs(self) -> List[Dict]:
        """列出缺少PDF的论文"""
        report = self.generate_status_report()
        
        missing_pdfs = []
        for status in report['status_list']:
            if status.has_json and not status.has_pdf:
                # 从数据库获取详细信息
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, title_cn, title_en, authors, venue, publication_year
                    FROM papers WHERE id = ?
                ''', (status.paper_id,))
                
                paper = cursor.fetchone()
                conn.close()
                
                if paper:
                    missing_pdfs.append({
                        'id': paper['id'],
                        'file_name': status.file_name,
                        'title_cn': paper['title_cn'],
                        'title_en': paper['title_en'],
                        'authors': paper['authors'],
                        'venue': paper['venue'],
                        'publication_year': paper['publication_year']
                    })
        
        return missing_pdfs
    
    def list_orphaned_pdfs(self) -> List[Dict]:
        """列出孤立的PDF文件（没有对应JSON的）"""
        report = self.generate_status_report()
        
        orphaned_pdfs = []
        for status in report['status_list']:
            if not status.has_json and status.has_pdf:
                pdf_path = Path(status.pdf_path)
                orphaned_pdfs.append({
                    'file_name': status.file_name,
                    'file_path': status.pdf_path,
                    'file_size': pdf_path.stat().st_size if pdf_path.exists() else 0,
                    'last_modified': datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat() if pdf_path.exists() else None
                })
        
        return orphaned_pdfs
    
    def organize_pdfs_by_status(self, output_dir: str):
        """按状态组织PDF文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        matched_dir = output_path / "matched_pdfs"
        orphaned_dir = output_path / "orphaned_pdfs"
        
        matched_dir.mkdir(exist_ok=True)
        orphaned_dir.mkdir(exist_ok=True)
        
        report = self.generate_status_report()
        
        copied_matched = 0
        copied_orphaned = 0
        
        for status in report['status_list']:
            if status.has_pdf:
                src_path = Path(status.pdf_path)
                
                if status.has_json:
                    # 有对应JSON的PDF
                    dst_path = matched_dir / src_path.name
                    shutil.copy2(src_path, dst_path)
                    copied_matched += 1
                else:
                    # 孤立的PDF
                    dst_path = orphaned_dir / src_path.name
                    shutil.copy2(src_path, dst_path)
                    copied_orphaned += 1
        
        logger.info(f"📁 PDF文件组织完成:")
        logger.info(f"  - 匹配的PDF: {copied_matched} 个 -> {matched_dir}")
        logger.info(f"  - 孤立的PDF: {copied_orphaned} 个 -> {orphaned_dir}")
        
        return {
            'matched_count': copied_matched,
            'orphaned_count': copied_orphaned,
            'matched_dir': str(matched_dir),
            'orphaned_dir': str(orphaned_dir)
        }
    
    def save_report(self, report: Dict, output_file: str):
        """保存报告到文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换PDFStatus对象为字典
        serializable_report = report.copy()
        serializable_report['status_list'] = [
            {
                'file_name': status.file_name,
                'has_json': status.has_json,
                'has_pdf': status.has_pdf,
                'json_path': status.json_path,
                'pdf_path': status.pdf_path,
                'paper_id': status.paper_id
            }
            for status in report['status_list']
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 报告已保存: {output_path}")

# 使用示例和测试函数
def test_pdf_manager():
    """测试PDF管理器功能"""
    manager = PDFManager()
    
    # 生成状态报告
    report = manager.generate_status_report()
    
    # 列出缺少PDF的论文
    missing = manager.list_missing_pdfs()
    print(f"\n❌ 缺少PDF的论文: {len(missing)} 篇")
    for paper in missing[:5]:  # 显示前5篇
        print(f"  - {paper['title_en'][:50]}...")
    
    # 列出孤立的PDF
    orphaned = manager.list_orphaned_pdfs()
    print(f"\n🔍 孤立的PDF文件: {len(orphaned)} 个")
    for pdf in orphaned[:5]:  # 显示前5个
        print(f"  - {pdf['file_name']}")

if __name__ == "__main__":
    test_pdf_manager()
