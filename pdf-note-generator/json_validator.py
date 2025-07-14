
# json_validator.py - 改进版本
import json
import os
import sys
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONValidator:
    def __init__(self):
        # 必需字段定义
        self.required_fields = {
            'file_name': str,
            'generated_at': str,
            'structured_info': dict
        }
        
        # structured_info 必需字段
        self.structured_info_required = {
            'title_cn': str,
            'title_en': str,
            'authors': list,
            'abstract': str,
            'publication_year': str
        }
        
        # 可选但重要的字段
        self.optional_important_fields = {
            'category': str,
            'topics': list,
            'keywords': list,
            'venue': str,
            'doi': str,
            'methodology': str,
            'conclusion': str
        }
        
        # 真正的错误模式（更精确的匹配）
        self.error_patterns = [
            r'^error\s*:',  # 以"error:"开头
            r'^failed\s*:',  # 以"failed:"开头
            r'^unable to process',  # 以"unable to process"开头
            r'^could not extract',  # 以"could not extract"开头
            r'extraction failed',  # 提取失败
            r'error processing file',  # 文件处理错误
            r'failed to parse',  # 解析失败
            r'unable to read',  # 读取失败
            r'no content found',  # 未找到内容
            r'invalid pdf',  # 无效PDF
            r'corrupted file',  # 损坏文件
            r'processing error',  # 处理错误
            r'timeout.*processing',  # 处理超时
        ]
        
        # 学术内容中的常见正常用词（白名单）
        self.academic_whitelist = [
            'failed to achieve',
            'unable to solve',
            'failed to converge',
            'unable to detect',
            'failed to establish',
            'unable to identify',
            'failed to improve',
            'unable to handle',
            'could not be found',
            'could not be determined',
            'could not be achieved',
            'error rate',
            'error analysis',
            'error correction',
            'error detection',
            'failure analysis',
            'failure mode',
            'failure detection',
        ]
    
    def validate_json_structure(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证JSON结构是否合规"""
        errors = []
        
        # 检查顶级必需字段
        for field, field_type in self.required_fields.items():
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
                continue
            
            if not isinstance(data[field], field_type):
                errors.append(f"字段类型错误: {field} 应该是 {field_type.__name__}")
        
        # 检查structured_info字段
        if 'structured_info' in data:
            structured_info = data['structured_info']
            
            for field, field_type in self.structured_info_required.items():
                if field not in structured_info:
                    errors.append(f"structured_info缺少必需字段: {field}")
                    continue
                
                if not isinstance(structured_info[field], field_type):
                    errors.append(f"structured_info字段类型错误: {field} 应该是 {field_type.__name__}")
        
        return len(errors) == 0, errors
    
    def is_real_error(self, text: str) -> bool:
        """判断文本是否包含真正的错误信息"""
        text_lower = text.lower()
        
        # 首先检查是否在白名单中（学术用词）
        for whitelist_phrase in self.academic_whitelist:
            if whitelist_phrase.lower() in text_lower:
                return False
        
        # 检查是否匹配错误模式
        for pattern in self.error_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # 检查特定的错误上下文
        error_contexts = [
            'error occurred while',
            'failed during processing',
            'unable to complete',
            'extraction process failed',
            'parsing error',
            'file corruption',
            'invalid format',
            'processing timeout',
            'memory error',
            'io error',
            'network error',
            'permission denied',
            'access denied',
            'file not found',
            'directory not found',
        ]
        
        for context in error_contexts:
            if context in text_lower:
                return True
        
        return False
    
    def validate_content_quality(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证内容质量"""
        warnings = []
        errors = []
        
        if 'structured_info' not in data:
            errors.append("没有structured_info字段")
            return False, errors
        
        info = data['structured_info']
        
        # 检查关键内容是否有效
        if 'title_en' in info:
            title_en = str(info['title_en']).strip()
            if not title_en or len(title_en) < 5:
                errors.append("英文标题太短或为空")
            elif self.is_real_error(title_en):
                errors.append(f"英文标题包含错误信息: {title_en[:50]}...")
        
        if 'title_cn' in info:
            title_cn = str(info['title_cn']).strip()
            if not title_cn or len(title_cn) < 3:
                warnings.append("中文标题太短或为空")
            elif self.is_real_error(title_cn):
                errors.append(f"中文标题包含错误信息: {title_cn[:50]}...")
        
        if 'authors' in info:
            authors = info['authors']
            if not authors or len(authors) == 0:
                errors.append("作者列表为空")
            elif isinstance(authors, list) and len(authors) > 0:
                # 检查作者是否有效
                valid_authors = []
                for author in authors:
                    if author and isinstance(author, str) and len(str(author).strip()) > 0:
                        if not self.is_real_error(str(author)):
                            valid_authors.append(author)
                
                if len(valid_authors) == 0:
                    errors.append("没有有效的作者信息")
        
        if 'abstract' in info:
            abstract = str(info['abstract']).strip()
            if not abstract or len(abstract) < 50:
                errors.append("摘要太短或为空")
            elif self.is_real_error(abstract):
                errors.append(f"摘要包含错误信息: {abstract[:100]}...")
        
        if 'publication_year' in info:
            year = info['publication_year']
            if isinstance(year, str):
                if not year.strip() or not year.strip().isdigit():
                    warnings.append("发表年份格式不正确")
                else:
                    year_int = int(year.strip())
                    if year_int < 1900 or year_int > 2030:
                        warnings.append(f"发表年份不合理: {year_int}")
        
        # 检查顶级字段是否包含错误信息
        if 'file_name' in data:
            file_name = str(data['file_name'])
            if self.is_real_error(file_name):
                errors.append(f"文件名包含错误信息: {file_name}")
        
        # 检查是否有明显的错误标识符（仅在非内容字段中）
        non_content_fields = ['file_name', 'generated_at', 'processing_info', 'errors']
        for field in non_content_fields:
            if field in data:
                field_text = str(data[field])
                if self.is_real_error(field_text):
                    errors.append(f"字段 {field} 包含错误信息: {field_text[:100]}...")
        
        return len(errors) == 0, errors + warnings
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """验证单个JSON文件"""
        result = {
            'file_path': file_path,
            'is_valid': False,
            'structure_valid': False,
            'content_valid': False,
            'errors': [],
            'warnings': [],
            'data': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result['data'] = data
            
            # 验证结构
            structure_valid, structure_errors = self.validate_json_structure(data)
            result['structure_valid'] = structure_valid
            result['errors'].extend(structure_errors)
            
            # 验证内容质量
            content_valid, content_issues = self.validate_content_quality(data)
            result['content_valid'] = content_valid
            
            # 分离错误和警告
            for issue in content_issues:
                if any(keyword in issue for keyword in ['错误', 'error', '缺少', '为空', '太短', '包含错误信息']):
                    result['errors'].append(issue)
                else:
                    result['warnings'].append(issue)
            
            result['is_valid'] = structure_valid and content_valid
            
        except json.JSONDecodeError as e:
            result['errors'].append(f"JSON格式错误: {str(e)}")
        except Exception as e:
            result['errors'].append(f"文件读取错误: {str(e)}")
        
        return result
    
    def validate_folder(self, folder_path: str) -> Dict[str, Any]:
        """验证文件夹中的所有JSON文件"""
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            return {
                'error': f"文件夹不存在: {folder_path}",
                'results': []
            }
        
        json_files = list(folder_path.glob('*.json'))
        results = []
        
        print(f"🔍 开始验证 {len(json_files)} 个JSON文件...")
        
        for i, json_file in enumerate(json_files):
            if i % 10 == 0 and i > 0:
                print(f"进度: {i}/{len(json_files)}")
            
            result = self.validate_file(str(json_file))
            results.append(result)
        
        # 统计结果
        total_files = len(results)
        valid_files = sum(1 for r in results if r['is_valid'])
        invalid_files = total_files - valid_files
        
        summary = {
            'total_files': total_files,
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'success_rate': valid_files / total_files * 100 if total_files > 0 else 0,
            'results': results
        }
        
        return summary
    
    def test_error_detection(self) -> None:
        """测试错误检测功能"""
        test_cases = [
            # 真正的错误
            ("Error: Failed to process PDF file", True),
            ("Failed to extract text from document", True),
            ("Unable to parse document structure", True),
            ("Processing error occurred", True),
            ("Extraction failed due to corruption", True),
            
            # 正常的学术内容
            ("Failed to achieve convergence in optimization", False),
            ("Unable to solve the NP-hard problem", False),
            ("The algorithm failed to improve performance", False),
            ("Error rate analysis shows improvements", False),
            ("Failure detection mechanism proposed", False),
            ("Could not be determined without additional data", False),
            ("The system was unable to handle large datasets", False),
            ("Performance degradation failed to meet expectations", False),
        ]
        
        print("🧪 测试错误检测功能:")
        for text, expected in test_cases:
            result = self.is_real_error(text)
            status = "✅" if result == expected else "❌"
            print(f"{status} '{text[:50]}...' -> {result} (预期: {expected})")
    
    def organize_files(self, source_folder: str, success_folder: str, failure_folder: str) -> Dict[str, Any]:
        """将JSON文件按验证结果分类到不同文件夹"""
        import shutil
        
        # 创建目标文件夹
        Path(success_folder).mkdir(parents=True, exist_ok=True)
        Path(failure_folder).mkdir(parents=True, exist_ok=True)
        
        # 验证文件夹
        validation_results = self.validate_folder(source_folder)
        
        if 'error' in validation_results:
            return validation_results
        
        moved_files = {'success': [], 'failure': []}
        
        for result in validation_results['results']:
            source_path = Path(result['file_path'])
            
            if result['is_valid']:
                # 移动到成功文件夹
                dest_path = Path(success_folder) / source_path.name
                shutil.move(str(source_path), str(dest_path))
                moved_files['success'].append(str(dest_path))
            else:
                # 移动到失败文件夹
                dest_path = Path(failure_folder) / source_path.name
                shutil.move(str(source_path), str(dest_path))
                moved_files['failure'].append(str(dest_path))
        
        return {
            'summary': validation_results,
            'moved_files': moved_files
        }
    
    def generate_report(self, validation_results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """生成验证报告"""
        if 'error' in validation_results:
            return f"验证失败: {validation_results['error']}"
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("📋 JSON文件验证报告")
        report_lines.append("=" * 60)
        
        # 总体统计
        report_lines.append(f"📊 总体统计:")
        report_lines.append(f"  - 总文件数: {validation_results['total_files']}")
        report_lines.append(f"  - 有效文件: {validation_results['valid_files']}")
        report_lines.append(f"  - 无效文件: {validation_results['invalid_files']}")
        report_lines.append(f"  - 成功率: {validation_results['success_rate']:.1f}%")
        report_lines.append("")
        
        # 无效文件详情
        if validation_results['invalid_files'] > 0:
            report_lines.append("❌ 无效文件详情:")
            for result in validation_results['results']:
                if not result['is_valid']:
                    report_lines.append(f"  📄 {Path(result['file_path']).name}")
                    for error in result['errors']:
                        report_lines.append(f"    - ❌ {error}")
                    for warning in result['warnings']:
                        report_lines.append(f"    - ⚠️ {warning}")
                    report_lines.append("")
        
        # 统计不同类型的错误
        error_types = {}
        for result in validation_results['results']:
            if not result['is_valid']:
                for error in result['errors']:
                    error_type = error.split(':')[0] if ':' in error else error.split(' ')[0]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            report_lines.append("📈 错误类型统计:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"  - {error_type}: {count} 次")
            report_lines.append("")
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"📄 报告已保存到: {output_file}")
        
        return report_text

def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JSON文件验证器 - 改进版')
    parser.add_argument('action', choices=['validate', 'organize', 'report', 'test'], 
                       help='操作类型')
    parser.add_argument('--source', '-s', 
                       help='源文件夹路径')
    parser.add_argument('--success', help='成功文件夹路径（仅用于organize）')
    parser.add_argument('--failure', help='失败文件夹路径（仅用于organize）')
    parser.add_argument('--output', '-o', help='报告输出文件路径')
    
    args = parser.parse_args()
    
    validator = JSONValidator()
    
    if args.action == 'test':
        validator.test_error_detection()
        return
    
    if not args.source:
        print("❌ 需要指定源文件夹路径 --source")
        return
    
    if args.action == 'validate':
        results = validator.validate_folder(args.source)
        if 'error' in results:
            print(f"❌ 验证失败: {results['error']}")
        else:
            print(f"\n✅ 验证完成: {results['success_rate']:.1f}% 通过率")
            print(f"  - 总文件数: {results['total_files']}")
            print(f"  - 有效文件: {results['valid_files']}")
            print(f"  - 无效文件: {results['invalid_files']}")
        
    elif args.action == 'organize':
        if not args.success or not args.failure:
            print("❌ organize操作需要指定 --success 和 --failure 参数")
            return
        
        results = validator.organize_files(args.source, args.success, args.failure)
        if 'error' in results:
            print(f"❌ 整理失败: {results['error']}")
        else:
            print(f"\n✅ 文件整理完成:")
            print(f"  - 成功文件: {len(results['moved_files']['success'])}")
            print(f"  - 失败文件: {len(results['moved_files']['failure'])}")
        
    elif args.action == 'report':
        results = validator.validate_folder(args.source)
        if 'error' in results:
            print(f"❌ 生成报告失败: {results['error']}")
        else:
            report = validator.generate_report(results, args.output)
            if not args.output:
                print(report)

if __name__ == '__main__':
    main()
