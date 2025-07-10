
import os
import logging
import warnings
from pathlib import Path
from typing import List, Dict, Optional, Callable
import time
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# 优化导入 - 抑制不必要的日志
warnings.filterwarnings('ignore')

# 设置pdfminer日志级别为ERROR以减少输出
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfminer.psparser').setLevel(logging.ERROR)
logging.getLogger('pdfminer.pdfinterp').setLevel(logging.ERROR)
logging.getLogger('pdfminer.converter').setLevel(logging.ERROR)

# 尝试多个PDF处理库
PDFPLUMBER_AVAILABLE = False
PYPDF2_AVAILABLE = False
PYMUPDF_AVAILABLE = False
PDFMINER_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pass

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    pass

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        pass

try:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    PDFMINER_AVAILABLE = True
except ImportError:
    pass

class OptimizedPDFProcessor:
    """优化的PDF处理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.processing_config = config.get('processing', {})
        self.max_pages = self.processing_config.get('max_pages', 30)
        self.chunk_size = self.processing_config.get('chunk_size', 2000)
        #此处设置pdf的处理方法，如果设置auto则后面使用最快的
        self.preferred_method = self.processing_config.get('pdf_method', 'pdfminer')
        
        self.use_ocr = self.processing_config.get('use_ocr', False)
        
        # 选择最佳的PDF处理方法
        self.pdf_method = self._select_pdf_method()
        
        # 设置日志抑制
        self._suppress_logs()
        
        print(f"🔧 使用PDF处理方法: {self.pdf_method}")
    
    def _suppress_logs(self):
        """抑制PDF处理库的详细日志"""
        # 抑制所有pdfminer相关的日志
        for logger_name in ['pdfminer', 'pdfminer.psparser', 'pdfminer.pdfinterp', 
                           'pdfminer.converter', 'pdfminer.pdfpage']:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)
            logger.disabled = True
        
        # 抑制其他可能的verbose输出
        os.environ['PDFMINER_LOG_LEVEL'] = 'ERROR'
    
    def _select_pdf_method(self) -> str:
        """选择最佳的PDF处理方法"""
        if self.preferred_method != 'auto':
            if self.preferred_method == 'pymupdf' and PYMUPDF_AVAILABLE:
                return 'pymupdf'
            elif self.preferred_method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
                return 'pdfplumber'
            elif self.preferred_method == 'pypdf2' and PYPDF2_AVAILABLE:
                return 'pypdf2'
            elif self.preferred_method == 'pdfminer' and PDFMINER_AVAILABLE:
                return 'pdfminer'
        
        # 按性能优先级排序
        if PYMUPDF_AVAILABLE:
            return 'pymupdf'  # 最快
        elif PDFPLUMBER_AVAILABLE:
            return 'pdfplumber'  # 准确度高
        elif PYPDF2_AVAILABLE:
            return 'pypdf2'  # 中等性能
        elif PDFMINER_AVAILABLE:
            return 'pdfminer'  # 最慢但最准确
        else:
            raise ImportError("没有可用的PDF处理库，请安装 pymupdf、pdfplumber、PyPDF2 或 pdfminer 中的任意一个")
    
    def extract_text(self, pdf_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """提取PDF文本 - 优化版"""
        try:
            if progress_callback:
                progress_callback(0, "开始提取文本")
            
            text = ""
            if self.pdf_method == 'pymupdf':
                text = self._extract_with_pymupdf(pdf_path, progress_callback)
            elif self.pdf_method == 'pdfplumber':
                text = self._extract_with_pdfplumber(pdf_path, progress_callback)
            elif self.pdf_method == 'pypdf2':
                text = self._extract_with_pypdf2(pdf_path, progress_callback)
            elif self.pdf_method == 'pdfminer':
                text = self._extract_with_pdfminer(pdf_path, progress_callback)
            
            if progress_callback:
                progress_callback(100, "文本提取完成")
            
            return text
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"提取失败: {str(e)}")
            raise
    
    def _extract_with_pymupdf(self, pdf_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """使用PyMuPDF提取文本 - 最快"""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF not available")
        
        import fitz
        
        text_parts = []
        doc = fitz.open(str(pdf_path))
        
        total_pages = min(len(doc), self.max_pages)
        
        for page_num in range(total_pages):
            if progress_callback:
                progress = (page_num + 1) / total_pages * 100
                progress_callback(progress, f"处理页面 {page_num + 1}/{total_pages}")
            
            page = doc[page_num]
            text = page.get_text()
            
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        return "\n".join(text_parts)
    
    def _extract_with_pdfplumber(self, pdf_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """使用pdfplumber提取文本 - 准确度高"""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber not available")
        
        text_parts = []
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            total_pages = min(len(pdf.pages), self.max_pages)
            
            for page_num in range(total_pages):
                if progress_callback:
                    progress = (page_num + 1) / total_pages * 100
                    progress_callback(progress, f"处理页面 {page_num + 1}/{total_pages}")
                
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                if text and text.strip():
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _extract_with_pypdf2(self, pdf_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """使用PyPDF2提取文本 - 中等性能"""
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 not available")
        
        text_parts = []
        
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            total_pages = min(len(reader.pages), self.max_pages)
            
            for page_num in range(total_pages):
                if progress_callback:
                    progress = (page_num + 1) / total_pages * 100
                    progress_callback(progress, f"处理页面 {page_num + 1}/{total_pages}")
                
                page = reader.pages[page_num]
                text = page.extract_text()
                
                if text and text.strip():
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _extract_with_pdfminer(self, pdf_path: Path, progress_callback: Optional[Callable] = None) -> str:
        """使用pdfminer提取文本 - 最准确但最慢"""
        if not PDFMINER_AVAILABLE:
            raise ImportError("pdfminer not available")
        
        # 重定向stderr到null以抑制debug输出
        import sys
        from io import StringIO
        
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            if progress_callback:
                progress_callback(50, "使用pdfminer提取文本")
            
            # 优化的LAParams设置
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                detect_vertical=True,
                all_texts=False
            )
            
            # 限制页面数量
            text = extract_text(
                str(pdf_path),
                maxpages=self.max_pages,
                laparams=laparams
            )
            
            if progress_callback:
                progress_callback(100, "pdfminer提取完成")
            
            return text
            
        finally:
            sys.stderr = old_stderr
    
    def chunk_text(self, text: str) -> List[str]:
        """分块处理文本"""
        if not text:
            return []
        
        # 清理文本
        text = self._clean_text(text)
        
        # 如果文本很短，不需要分块
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        sentences = text.split('.')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk += sentence + "."
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "."
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符，保留常见标点和字母数字
        # 修复正则表达式：正确处理字符类中的特殊字符
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\'"]', ' ', text)
        
        # 移除多余的空行
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    def get_pdf_info(self, pdf_path: Path) -> Dict:
        """获取PDF信息"""
        info = {
            'file_size': pdf_path.stat().st_size,
            'file_name': pdf_path.name,
            'method_used': self.pdf_method,
            'pages': 0,
            'has_text': False
        }
        
        try:
            if self.pdf_method == 'pymupdf' and PYMUPDF_AVAILABLE:
                import fitz
                doc = fitz.open(str(pdf_path))
                info['pages'] = len(doc)
                info['has_text'] = any(doc[i].get_text().strip() for i in range(min(3, len(doc))))
                doc.close()
            elif self.pdf_method == 'pdfplumber' and PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(str(pdf_path)) as pdf:
                    info['pages'] = len(pdf.pages)
                    info['has_text'] = any(page.extract_text() for page in pdf.pages[:3])
            elif self.pdf_method == 'pypdf2' and PYPDF2_AVAILABLE:
                with open(pdf_path, 'rb') as file:
                    reader = PdfReader(file)
                    info['pages'] = len(reader.pages)
                    info['has_text'] = any(page.extract_text().strip() for page in reader.pages[:3])
            
        except Exception as e:
            info['error'] = str(e)
        
        return info

class AsyncPDFProcessor:
    """异步PDF处理器"""
    
    def __init__(self, config: Dict, max_workers: Optional[int] = None):
        self.config = config
        self.max_workers = max_workers or min(4, mp.cpu_count())
        self.processor = OptimizedPDFProcessor(config)
    
    def process_multiple_pdfs(self, pdf_paths: List[Path], progress_callback: Optional[Callable] = None) -> List[Dict]:
        """并发处理多个PDF文件"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_pdf = {
                executor.submit(self._process_single_pdf, pdf_path): pdf_path 
                for pdf_path in pdf_paths
            }
            
            # 收集结果
            for i, future in enumerate(as_completed(future_to_pdf)):
                pdf_path = future_to_pdf[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + 1, len(pdf_paths), pdf_path.name)
                        
                except Exception as e:
                    results.append({
                        'pdf_path': pdf_path,
                        'error': str(e),
                        'success': False
                    })
        
        return results
    
    def _process_single_pdf(self, pdf_path: Path) -> Dict:
        """处理单个PDF文件"""
        try:
            start_time = time.time()
            
            # 获取PDF信息
            pdf_info = self.processor.get_pdf_info(pdf_path)
            
            # 提取文本
            text = self.processor.extract_text(pdf_path)
            
            # 分块
            chunks = self.processor.chunk_text(text)
            
            processing_time = time.time() - start_time
            
            return {
                'pdf_path': pdf_path,
                'text': text,
                'chunks': chunks,
                'pdf_info': pdf_info,
                'processing_time': processing_time,
                'success': True
            }
            
        except Exception as e:
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }

def get_available_pdf_methods() -> List[str]:
    """获取可用的PDF处理方法"""
    available_methods = []
    
    if PYMUPDF_AVAILABLE:
        available_methods.append('pymupdf')
    if PDFPLUMBER_AVAILABLE:
        available_methods.append('pdfplumber')
    if PYPDF2_AVAILABLE:
        available_methods.append('pypdf2')
    if PDFMINER_AVAILABLE:
        available_methods.append('pdfminer')
    
    return available_methods

def test_pdf_processing(pdf_path: Path, config: Dict) -> Dict:
    """测试PDF处理"""
    processor = OptimizedPDFProcessor(config)
    
    try:
        start_time = time.time()
        
        # 获取PDF信息
        pdf_info = processor.get_pdf_info(pdf_path)
        
        # 提取文本
        text = processor.extract_text(pdf_path)
        
        # 分块
        chunks = processor.chunk_text(text)
        
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'method': processor.pdf_method,
            'pdf_info': pdf_info,
            'text_length': len(text),
            'chunks_count': len(chunks),
            'processing_time': processing_time
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': processor.pdf_method
        }

if __name__ == "__main__":
    # 测试代码
    print("🔍 检查可用的PDF处理方法:")
    methods = get_available_pdf_methods()
    for method in methods:
        print(f"  ✅ {method}")
    
    if not methods:
        print("  ❌ 没有可用的PDF处理库")
        print("  💡 请安装: pip install pymupdf pdfplumber PyPDF2 pdfminer.six")
    else:
        print(f"\n🎯 推荐使用: {methods[0]} (性能最优)")
