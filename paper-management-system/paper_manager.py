
# paper_manager.py - 修复年份数据类型问题

import os
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import markdown
from collections import defaultdict, Counter
import os
from flask import send_from_directory, abort
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'paper-manager-secret-key'
app.config['JSON_FOLDER'] = 'json_papers'  # JSON文件存储文件夹
app.config['DATABASE'] = 'papers.db'

# 配置PDF文件夹路径
PDF_FOLDER = 'pdfs'
# 确保必要的文件夹存在
os.makedirs(app.config['JSON_FOLDER'], exist_ok=True)

class PaperManager:
    """论文管理核心类"""
    
    def __init__(self, db_path='papers.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建论文表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                title_cn TEXT,
                title_en TEXT,
                category TEXT,
                topics TEXT,  -- JSON格式存储
                keywords TEXT,  -- JSON格式存储
                abstract TEXT,
                methodology TEXT,
                conclusion TEXT,
                authors TEXT,  -- JSON格式存储
                publication_year INTEGER,
                venue TEXT,
                doi TEXT,
                bibtex_citation TEXT,
                analysis TEXT,  -- JSON格式存储完整分析
                json_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_cn ON papers(title_cn)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_en ON papers(title_en)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON papers(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON papers(publication_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_venue ON papers(venue)')
        
        conn.commit()
        conn.close()
    
    def load_json_file(self, json_path):
        """加载JSON文件"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载JSON文件失败: {json_path}, 错误: {e}")
            return None
    
    def parse_structured_info(self, structured_info_str):
        """解析结构化信息字符串"""
        try:
            if isinstance(structured_info_str, str):
                return json.loads(structured_info_str)
            elif isinstance(structured_info_str, dict):
                return structured_info_str
            else:
                return {}
        except Exception as e:
            print(f"解析structured_info失败: {e}")
            return {}
    
    def convert_indexed_dict_to_list(self, indexed_dict):
        """将索引字典转换为列表"""
        if not indexed_dict:
            return []
        
        if isinstance(indexed_dict, list):
            return indexed_dict
        
        if isinstance(indexed_dict, dict):
            # 如果是索引字典 {"0": "value1", "1": "value2"}
            try:
                # 尝试按数字索引排序
                max_key = max(int(k) for k in indexed_dict.keys() if k.isdigit())
                result = []
                for i in range(max_key + 1):
                    if str(i) in indexed_dict:
                        result.append(indexed_dict[str(i)])
                return result
            except:
                # 如果不是数字索引，返回所有值
                return list(indexed_dict.values())
        
        return []
    
    def safe_int(self, value, default=0):
        """安全地转换为整数"""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                # 处理字符串类型的年份
                value = value.strip()
                if not value:
                    return default
                # 只取数字部分
                import re
                match = re.search(r'\d{4}', value)
                if match:
                    return int(match.group())
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def import_json_file(self, json_path):
        """导入单个JSON文件到数据库"""
        data = self.load_json_file(json_path)
        if not data:
            return False
        
        # 解析结构化信息
        structured_info = self.parse_structured_info(data.get('structured_info', '{}'))
        
        # 处理 topics (可能是索引字典)
        topics_raw = structured_info.get('topics', [])
        topics_list = self.convert_indexed_dict_to_list(topics_raw)
        
        # 处理 keywords (可能是索引字典)
        keywords_raw = structured_info.get('keywords', [])
        keywords_list = self.convert_indexed_dict_to_list(keywords_raw)
        
        # 处理 authors (可能是索引字典)
        authors_raw = structured_info.get('authors', [])
        authors_list = self.convert_indexed_dict_to_list(authors_raw)
        
        # 处理 analysis (可能是字符串)
        analysis_raw = structured_info.get('analysis', {})
        if isinstance(analysis_raw, str):
            try:
                analysis_dict = json.loads(analysis_raw)
            except:
                analysis_dict = {}
        else:
            analysis_dict = analysis_raw
        
        # 安全处理年份
        publication_year = self.safe_int(structured_info.get('publication_year', 0))
        
        # 提取信息
        paper_data = {
            'file_name': data.get('file_name', ''),
            'title_cn': structured_info.get('title_cn', ''),
            'title_en': structured_info.get('title_en', ''),
            'category': structured_info.get('category', ''),
            'topics': json.dumps(topics_list, ensure_ascii=False),
            'keywords': json.dumps(keywords_list, ensure_ascii=False),
            'abstract': structured_info.get('abstract', ''),
            'methodology': structured_info.get('methodology', ''),
            'conclusion': structured_info.get('conclusion', ''),
            'authors': json.dumps(authors_list, ensure_ascii=False),
            'publication_year': publication_year,
            'venue': structured_info.get('venue', ''),
            'doi': structured_info.get('doi', ''),
            'bibtex_citation': structured_info.get('bibtex_citation', ''),
            'analysis': json.dumps(analysis_dict, ensure_ascii=False),
            'json_path': str(json_path)
        }
        
        # 插入数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM papers WHERE json_path = ?', (str(json_path),))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE papers SET 
                    file_name=?, title_cn=?, title_en=?, category=?, topics=?, keywords=?,
                    abstract=?, methodology=?, conclusion=?, authors=?, publication_year=?,
                    venue=?, doi=?, bibtex_citation=?, analysis=?, updated_at=CURRENT_TIMESTAMP
                WHERE json_path=?
            ''', (
                paper_data['file_name'], paper_data['title_cn'], paper_data['title_en'],
                paper_data['category'], paper_data['topics'], paper_data['keywords'],
                paper_data['abstract'], paper_data['methodology'], paper_data['conclusion'],
                paper_data['authors'], paper_data['publication_year'], paper_data['venue'],
                paper_data['doi'], paper_data['bibtex_citation'], paper_data['analysis'],
                str(json_path)
            ))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO papers (
                    file_name, title_cn, title_en, category, topics, keywords,
                    abstract, methodology, conclusion, authors, publication_year,
                    venue, doi, bibtex_citation, analysis, json_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                paper_data['file_name'], paper_data['title_cn'], paper_data['title_en'],
                paper_data['category'], paper_data['topics'], paper_data['keywords'],
                paper_data['abstract'], paper_data['methodology'], paper_data['conclusion'],
                paper_data['authors'], paper_data['publication_year'], paper_data['venue'],
                paper_data['doi'], paper_data['bibtex_citation'], paper_data['analysis'],
                str(json_path)
            ))
        
        conn.commit()
        conn.close()
        return True
    
    def import_json_folder(self, folder_path):
        """批量导入JSON文件夹"""
        folder_path = Path(folder_path)
        if not folder_path.exists():
            return 0, [f"路径不存在: {folder_path}"]
        
        json_files = list(folder_path.rglob('*.json'))
        if not json_files:
            return 0, [f"在路径 {folder_path} 中没有找到JSON文件"]
        
        imported_count = 0
        failed_files = []
        
        print(f"找到 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            try:
                print(f"正在导入: {json_file}")
                if self.import_json_file(json_file):
                    imported_count += 1
                    print(f"成功导入: {json_file}")
                else:
                    failed_files.append(str(json_file))
                    print(f"导入失败: {json_file}")
            except Exception as e:
                failed_files.append(f"{json_file}: {e}")
                print(f"导入异常: {json_file}: {e}")
        
        print(f"导入完成: {imported_count} 个成功, {len(failed_files)} 个失败")
        return imported_count, failed_files
    
    def check_pdf_exists(self, pdf_filename):
        """检查PDF文件是否存在"""
        if not pdf_filename:
            return False
        
        # 如果文件名以.json结尾，替换为.pdf
        if pdf_filename.endswith('.json'):
            pdf_filename = pdf_filename[:-5] + '.pdf'
        elif not pdf_filename.endswith('.pdf'):
            pdf_filename += '.pdf'
        
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)
        return os.path.exists(pdf_path)

    def get_pdf_filename(self, json_filename):
        """从JSON文件名获取PDF文件名"""
        if not json_filename:
            return None
        
        # 如果文件名以.json结尾，替换为.pdf
        if json_filename.endswith('.json'):
            pdf_filename = json_filename[:-5] + '.pdf'
        elif not json_filename.endswith('.pdf'):
            pdf_filename = json_filename + '.pdf'
        else:
            pdf_filename = json_filename
        
        return pdf_filename




    def search_papers(self, query='', category='', author='', venue='', year_range=None, limit=50, offset=0):
        """搜索论文 - 增强版 (增加期刊搜索)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        # 关键词搜索
        if query:
            conditions.append('''
                (title_cn LIKE ? OR title_en LIKE ? OR abstract LIKE ? OR 
                keywords LIKE ? OR authors LIKE ? OR venue LIKE ? OR methodology LIKE ? OR conclusion LIKE ?)
            ''')
            query_param = f'%{query}%'
            params.extend([query_param] * 8)
        
        # 分类搜索
        if category:
            conditions.append('category = ?')
            params.append(category)
        
        # 作者搜索
        if author:
            conditions.append('authors LIKE ?')
            params.append(f'%{author}%')
        
        # 期刊搜索 - 新增
        if venue:
            conditions.append('venue = ?')
            params.append(venue)
        
        # 年份范围
        if year_range:
            if year_range[0]:
                conditions.append('publication_year >= ?')
                params.append(year_range[0])
            if year_range[1]:
                conditions.append('publication_year <= ?')
                params.append(year_range[1])
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 获取总数
        cursor.execute(f'SELECT COUNT(*) FROM papers WHERE {where_clause}', params)
        total_count = cursor.fetchone()[0]
        
        # 获取结果
        cursor.execute(f'''
            SELECT * FROM papers WHERE {where_clause}
            ORDER BY publication_year DESC, title_en
            LIMIT ? OFFSET ?
        ''', params + [limit, offset])
        
        papers = [dict(row) for row in cursor.fetchall()]
        
        # 解析作者信息
        for paper in papers:
            try:
                paper['authors_list'] = json.loads(paper['authors']) if paper['authors'] else []
            except:
                paper['authors_list'] = []
        
        conn.close()
        
        return papers, total_count
    

    def parse_analysis_content(self, analysis_data):
        """解析分析内容，处理不同数据结构"""
        if not analysis_data:
            return {}
        
        parsed_analysis = {}
        
        for key, value in analysis_data.items():
            # 格式化标题
            formatted_key = self.format_analysis_title(key)
            
            # 处理不同类型的值
            if isinstance(value, str):
                # 字符串直接使用
                parsed_analysis[formatted_key] = {
                    'type': 'text',
                    'content': value
                }
            elif isinstance(value, list):
                # 处理列表
                parsed_analysis[formatted_key] = self.parse_list_content(value)
            else:
                # 其他类型转为字符串
                parsed_analysis[formatted_key] = {
                    'type': 'text',
                    'content': str(value)
                }
        
        return parsed_analysis

    def format_analysis_title(self, title):
        """格式化分析标题"""
        # 将下划线替换为空格，并首字母大写
        formatted = title.replace('_', ' ').replace('-', ' ')
        # 每个单词首字母大写
        formatted = ' '.join(word.capitalize() for word in formatted.split())
        return formatted

    def parse_list_content(self, content_list):
        """解析列表内容"""
        if not content_list:
            return {'type': 'text', 'content': ''}
        
        parsed_items = []
        
        for item in content_list:
            if isinstance(item, str):
                # 字符串项
                parsed_items.append({
                    'type': 'text',
                    'content': item
                })
            elif isinstance(item, list):
                # 嵌套列表
                if len(item) == 1:
                    # 单项列表
                    parsed_items.append({
                        'type': 'text',
                        'content': str(item[0])
                    })
                else:
                    # 多项列表，作为子列表
                    parsed_items.append({
                        'type': 'sublist',
                        'content': item
                    })
            else:
                # 其他类型
                parsed_items.append({
                    'type': 'text',
                    'content': str(item)
                })
        
        return {
            'type': 'list',
            'items': parsed_items
        }





    def get_all_venues(self):
        """获取所有期刊/会议列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT venue FROM papers 
            WHERE venue != '' AND venue IS NOT NULL
            ORDER BY venue
        ''')
        venues = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return venues

    def get_papers_by_venue(self, venue_name, limit=50, offset=0):
        """根据期刊获取论文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM papers 
            WHERE venue = ?
        ''', (venue_name,))
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT * FROM papers 
            WHERE venue = ?
            ORDER BY publication_year DESC, title_en
            LIMIT ? OFFSET ?
        ''', (venue_name, limit, offset))
        
        papers = [dict(row) for row in cursor.fetchall()]
        
        # 解析作者信息
        for paper in papers:
            try:
                paper['authors_list'] = json.loads(paper['authors']) if paper['authors'] else []
            except:
                paper['authors_list'] = []
        
        conn.close()
        return papers, total_count

    def get_venue_statistics(self):
        """获取期刊统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT venue, COUNT(*) as count 
            FROM papers 
            WHERE venue != '' AND venue IS NOT NULL
            GROUP BY venue 
            ORDER BY count DESC, venue
        ''')
        
        venue_stats = cursor.fetchall()
        conn.close()
        
        return venue_stats










    def get_all_authors(self):
        """获取所有作者列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT authors FROM papers WHERE authors != ""')
        authors_json_list = cursor.fetchall()
        
        all_authors = set()
        for (authors_json,) in authors_json_list:
            try:
                authors = json.loads(authors_json)
                if isinstance(authors, list):
                    for author in authors:
                        if author.strip():
                            all_authors.add(author.strip())
            except:
                continue
        
        conn.close()
        return sorted(list(all_authors))

    def get_papers_by_author(self, author_name, limit=50, offset=0):
        """根据作者获取论文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM papers 
            WHERE authors LIKE ?
        ''', (f'%{author_name}%',))
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT * FROM papers 
            WHERE authors LIKE ?
            ORDER BY publication_year DESC, title_en
            LIMIT ? OFFSET ?
        ''', (f'%{author_name}%', limit, offset))
        
        papers = [dict(row) for row in cursor.fetchall()]
        
        # 解析作者信息
        for paper in papers:
            try:
                paper['authors_list'] = json.loads(paper['authors']) if paper['authors'] else []
            except:
                paper['authors_list'] = []
        
        conn.close()
        return papers, total_count



    def find_duplicate_papers(self):
        """查找重复论文（基于DOI）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找有相同DOI的论文组
        cursor.execute('''
            SELECT doi, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM papers 
            WHERE doi != '' AND doi IS NOT NULL
            GROUP BY doi 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        ''')
        
        duplicates = []
        for row in cursor.fetchall():
            doi, count, ids_str = row
            ids = [int(id) for id in ids_str.split(',')]
            
            # 获取这些重复论文的详细信息
            cursor.execute('''
                SELECT id, title_cn, title_en, file_name, created_at, updated_at
                FROM papers 
                WHERE id IN ({})
                ORDER BY updated_at DESC
            '''.format(','.join(['?'] * len(ids))), ids)
            
            papers = cursor.fetchall()
            duplicates.append({
                'doi': doi,
                'count': count,
                'papers': papers
            })
        
        conn.close()
        return duplicates

    def find_duplicate_papers_by_title(self):
        """基于标题查找可能的重复论文"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找有相同标题的论文
        cursor.execute('''
            SELECT title_en, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM papers 
            WHERE title_en != '' AND title_en IS NOT NULL
            GROUP BY LOWER(title_en)
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        ''')
        
        duplicates = []
        for row in cursor.fetchall():
            title, count, ids_str = row
            ids = [int(id) for id in ids_str.split(',')]
            
            cursor.execute('''
                SELECT id, title_cn, title_en, file_name, doi, created_at, updated_at
                FROM papers 
                WHERE id IN ({})
                ORDER BY updated_at DESC
            '''.format(','.join(['?'] * len(ids))), ids)
            
            papers = cursor.fetchall()
            duplicates.append({
                'title': title,
                'count': count,
                'papers': papers
            })
        
        conn.close()
        return duplicates

    def auto_deduplicate_by_doi(self):
        """自动去重：基于DOI，保留最新版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        removed_count = 0
        duplicates = self.find_duplicate_papers()
        
        for duplicate in duplicates:
            papers = duplicate['papers']
            if len(papers) > 1:
                # 保留最新的（第一个，因为已经按updated_at DESC排序）
                keep_paper = papers[0]
                remove_papers = papers[1:]
                
                # 删除旧版本
                for paper in remove_papers:
                    cursor.execute('DELETE FROM papers WHERE id = ?', (paper[0],))
                    removed_count += 1
                    print(f"删除重复论文: {paper[3]} (ID: {paper[0]})")
        
        conn.commit()
        conn.close()
        
        return removed_count

    def merge_paper_data(self, keep_id, remove_id):
        """合并论文数据（保留较完整的数据）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取两篇论文的数据
        cursor.execute('SELECT * FROM papers WHERE id = ?', (keep_id,))
        keep_paper = cursor.fetchone()
        
        cursor.execute('SELECT * FROM papers WHERE id = ?', (remove_id,))
        remove_paper = cursor.fetchone()
        
        if not keep_paper or not remove_paper:
            conn.close()
            return False
        
        # 合并数据的逻辑（选择非空的字段）
        merged_data = {}
        columns = [desc[0] for desc in cursor.description]
        
        for i, column in enumerate(columns):
            if column == 'id':
                merged_data[column] = keep_paper[i]
            elif column in ['created_at', 'updated_at']:
                # 保留较新的时间
                merged_data[column] = max(keep_paper[i], remove_paper[i])
            else:
                # 选择非空的值，如果都非空则保留keep_paper的值
                keep_value = keep_paper[i]
                remove_value = remove_paper[i]
                
                if not keep_value and remove_value:
                    merged_data[column] = remove_value
                else:
                    merged_data[column] = keep_value
        
        # 更新保留的论文
        update_fields = [f"{col} = ?" for col in columns if col != 'id']
        update_values = [merged_data[col] for col in columns if col != 'id']
        update_values.append(keep_id)
        
        cursor.execute(f'''
            UPDATE papers SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)
        
        # 删除要移除的论文
        cursor.execute('DELETE FROM papers WHERE id = ?', (remove_id,))
        
        conn.commit()
        conn.close()
        
        return True

    def get_deduplication_stats(self):
        """获取去重统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 总论文数
        cursor.execute('SELECT COUNT(*) FROM papers')
        stats['total_papers'] = cursor.fetchone()[0]
        
        # 有DOI的论文数
        cursor.execute('SELECT COUNT(*) FROM papers WHERE doi != "" AND doi IS NOT NULL')
        stats['papers_with_doi'] = cursor.fetchone()[0]
        
        # DOI重复的论文组数
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT doi FROM papers 
                WHERE doi != "" AND doi IS NOT NULL
                GROUP BY doi 
                HAVING COUNT(*) > 1
            )
        ''')
        stats['duplicate_doi_groups'] = cursor.fetchone()[0]
        
        # 标题重复的论文组数
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT title_en FROM papers 
                WHERE title_en != "" AND title_en IS NOT NULL
                GROUP BY LOWER(title_en)
                HAVING COUNT(*) > 1
            )
        ''')
        stats['duplicate_title_groups'] = cursor.fetchone()[0]
        
        conn.close()
        return stats




    def get_paper_by_id(self, paper_id):
        """根据ID获取论文详情"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM papers WHERE id = ?', (paper_id,))
        paper = cursor.fetchone()
        conn.close()
        
        if paper:
            return dict(paper)
        return None
    

    def get_statistics(self):
        """获取统计信息 - 增强版"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 总论文数
        cursor.execute('SELECT COUNT(*) FROM papers')
        stats['total_papers'] = cursor.fetchone()[0]
        
        # 按年份统计
        cursor.execute('''
            SELECT publication_year, COUNT(*) as count 
            FROM papers 
            WHERE publication_year > 0 
            GROUP BY publication_year 
            ORDER BY publication_year DESC
        ''')
        year_results = cursor.fetchall()
        stats['by_year'] = {}
        for year, count in year_results:
            stats['by_year'][str(year)] = count
        
        # 按类别统计
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM papers 
            WHERE category != '' 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        category_results = cursor.fetchall()
        stats['by_category'] = dict(category_results)
        stats['top_categories'] = category_results[:10]
        
        # 按期刊统计 - 增强版
        cursor.execute('''
            SELECT venue, COUNT(*) as count 
            FROM papers 
            WHERE venue != '' AND venue IS NOT NULL
            GROUP BY venue 
            ORDER BY count DESC
        ''')
        venue_results = cursor.fetchall()
        stats['by_venue'] = dict(venue_results)
        stats['top_venues'] = venue_results[:15]  # 显示前15个期刊
        
        # 为模板准备前10个年份
        stats['top_years'] = [(str(year), count) for year, count in year_results[:10]]
        
        conn.close()
        return stats

# 全局实例
paper_manager = PaperManager()

@app.route('/')
def index():
    """主页"""
    try:
        stats = paper_manager.get_statistics()
        return render_template('index.html', stats=stats)
    except Exception as e:
        print(f"主页错误: {e}")
        import traceback
        traceback.print_exc()
        return f"主页加载错误: {e}", 500


# 修改搜索路由
@app.route('/search')
def search():
    """搜索页面 - 增强版"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    author = request.args.get('author', '')
    venue = request.args.get('venue', '')  # 新增
    year_start = request.args.get('year_start', '')
    year_end = request.args.get('year_end', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # 处理年份范围
    year_range = [None, None]
    if year_start:
        try:
            year_range[0] = int(year_start)
        except ValueError:
            pass
    if year_end:
        try:
            year_range[1] = int(year_end)
        except ValueError:
            pass
    
    # 搜索
    offset = (page - 1) * per_page
    papers, total_count = paper_manager.search_papers(
        query=query,
        category=category,
        author=author,
        venue=venue,  # 新增
        year_range=year_range,
        limit=per_page,
        offset=offset
    )
    
    # 分页信息
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('search.html',
                         papers=papers,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         query=query,
                         category=category,
                         author=author,
                         venue=venue,  # 新增
                         year_start=year_start,
                         year_end=year_end)

@app.route('/venue/<venue_name>')
def venue_papers(venue_name):
    """期刊论文页面"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    offset = (page - 1) * per_page
    papers, total_count = paper_manager.get_papers_by_venue(
        venue_name=venue_name,
        limit=per_page,
        offset=offset
    )
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('venue_papers.html',
                         papers=papers,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         venue_name=venue_name)

@app.route('/api/venue_suggestions')
def api_venue_suggestions():
    """API: 期刊搜索建议"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    all_venues = paper_manager.get_all_venues()
    suggestions = [venue for venue in all_venues if query.lower() in venue.lower()]
    
    return jsonify(suggestions[:10])


@app.route('/author/<author_name>')
def author_papers(author_name):
    """作者论文页面"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    offset = (page - 1) * per_page
    papers, total_count = paper_manager.get_papers_by_author(
        author_name=author_name,
        limit=per_page,
        offset=offset
    )
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('author_papers.html',
                         papers=papers,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         author_name=author_name)

@app.route('/api/authors')
def api_authors():
    """API: 获取所有作者"""
    authors = paper_manager.get_all_authors()
    return jsonify(authors)

@app.route('/api/author_suggestions')
def api_author_suggestions():
    """API: 作者搜索建议"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    all_authors = paper_manager.get_all_authors()
    suggestions = [author for author in all_authors if query.lower() in author.lower()]
    
    return jsonify(suggestions[:10])



@app.route('/paper/<int:paper_id>')
def paper_detail(paper_id):
    """论文详情页 - 增加PDF链接"""
    paper = paper_manager.get_paper_by_id(paper_id)
    if not paper:
        return "论文不存在", 404
    
    # 解析JSON字段
    try:
        paper['topics'] = json.loads(paper['topics']) if paper['topics'] else []
        paper['keywords'] = json.loads(paper['keywords']) if paper['keywords'] else []
        paper['authors'] = json.loads(paper['authors']) if paper['authors'] else []
        
        # 解析分析内容
        analysis_raw = paper.get('analysis', '')
        if isinstance(analysis_raw, str):
            if analysis_raw.strip():
                try:
                    paper['analysis'] = json.loads(analysis_raw)
                except json.JSONDecodeError:
                    paper['analysis'] = {}
            else:
                paper['analysis'] = {}
        elif isinstance(analysis_raw, dict):
            paper['analysis'] = analysis_raw
        else:
            paper['analysis'] = {}
        
        # 添加PDF信息
        paper['pdf_filename'] = paper_manager.get_pdf_filename(paper['file_name'])
        paper['pdf_exists'] = paper_manager.check_pdf_exists(paper['file_name'])
        
        paper['parsed_analysis'] = None
        
    except Exception as e:
        print(f"解析论文数据失败: {e}")
        paper['topics'] = []
        paper['keywords'] = []
        paper['authors'] = []
        paper['analysis'] = {}
        paper['parsed_analysis'] = None
        paper['pdf_filename'] = None
        paper['pdf_exists'] = False
    
    return render_template('paper_detail.html', paper=paper)

# 添加PDF文件夹状态检查的API
@app.route('/api/pdf-status')
def pdf_status():
    """检查PDF文件夹状态"""
    try:
        if not os.path.exists(PDF_FOLDER):
            return jsonify({
                'status': 'folder_not_exists',
                'message': 'PDF文件夹不存在',
                'pdf_count': 0
            })
        
        pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
        
        return jsonify({
            'status': 'ok',
            'message': f'PDF文件夹正常，共{len(pdf_files)}个文件',
            'pdf_count': len(pdf_files),
            'pdf_files': pdf_files
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'pdf_count': 0
        })








# 添加PDF服务路由
@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """提供PDF文件下载/查看"""
    try:
        # 确保文件名安全
        filename = os.path.basename(filename)
        
        # 检查文件是否存在
        pdf_path = os.path.join(PDF_FOLDER, filename)
        if not os.path.exists(pdf_path):
            abort(404)
        
        # 返回文件，支持在线预览
        return send_from_directory(PDF_FOLDER, filename, as_attachment=False)
    
    except Exception as e:
        print(f"PDF服务错误: {e}")
        abort(404)

@app.route('/pdf/<filename>/download')
def download_pdf(filename):
    """下载PDF文件"""
    try:
        # 确保文件名安全
        filename = os.path.basename(filename)
        
        # 检查文件是否存在
        pdf_path = os.path.join(PDF_FOLDER, filename)
        if not os.path.exists(pdf_path):
            abort(404)
        
        # 返回文件作为附件下载
        return send_from_directory(PDF_FOLDER, filename, as_attachment=True)
    
    except Exception as e:
        print(f"PDF下载错误: {e}")
        abort(404)
    
    return render_template('paper_detail.html', paper=paper)

@app.route('/import', methods=['GET', 'POST'])
def import_papers():
    """导入论文"""
    if request.method == 'POST':
        folder_path = request.form.get('folder_path', '').strip()
        
        if not folder_path:
            return render_template('import.html', error='请输入文件夹路径')
        
        try:
            imported_count, failed_files = paper_manager.import_json_folder(folder_path)
            
            return render_template('import.html',
                                 success=f'成功导入 {imported_count} 个论文',
                                 failed_files=failed_files)
        except Exception as e:
            return render_template('import.html', error=f'导入失败: {str(e)}')
    
    return render_template('import.html')

@app.route('/statistics')
def statistics():
    """统计页面"""
    try:
        stats = paper_manager.get_statistics()
        return render_template('statistics.html', stats=stats)
    except Exception as e:
        print(f"统计页面错误: {e}")
        import traceback
        traceback.print_exc()
        return f"统计页面加载错误: {e}", 500

@app.route('/api/categories')
def api_categories():
    """API: 获取所有分类"""
    conn = sqlite3.connect(paper_manager.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM papers WHERE category != "" ORDER BY category')
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)

@app.route('/api/venues')
def api_venues():
    """API: 获取所有期刊"""
    conn = sqlite3.connect(paper_manager.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT venue FROM papers WHERE venue != "" ORDER BY venue')
    venues = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(venues)

@app.route('/api/search_suggestions')
def api_search_suggestions():
    """API: 搜索建议"""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = sqlite3.connect(paper_manager.db_path)
    cursor = conn.cursor()
    
    # 搜索标题建议
    cursor.execute('''
        SELECT DISTINCT title_cn as title FROM papers 
        WHERE title_cn LIKE ? AND title_cn != ""
        UNION
        SELECT DISTINCT title_en as title FROM papers 
        WHERE title_en LIKE ? AND title_en != ""
        LIMIT 10
    ''', (f'%{query}%', f'%{query}%'))
    
    suggestions = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(suggestions)

@app.route('/deduplication')
def deduplication_page():
    """去重管理页面"""
    stats = paper_manager.get_deduplication_stats()
    doi_duplicates = paper_manager.find_duplicate_papers()
    title_duplicates = paper_manager.find_duplicate_papers_by_title()
    
    return render_template('deduplication.html',
                         stats=stats,
                         doi_duplicates=doi_duplicates,
                         title_duplicates=title_duplicates)

@app.route('/api/auto-deduplicate', methods=['POST'])
def auto_deduplicate():
    """API: 自动去重"""
    try:
        removed_count = paper_manager.auto_deduplicate_by_doi()
        return jsonify({
            'success': True,
            'message': f'成功删除 {removed_count} 篇重复论文',
            'removed_count': removed_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'去重失败: {str(e)}'
        })

@app.route('/api/merge-papers', methods=['POST'])
def merge_papers():
    """API: 合并论文"""
    try:
        data = request.get_json()
        keep_id = data.get('keep_id')
        remove_id = data.get('remove_id')
        
        if not keep_id or not remove_id:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            })
        
        success = paper_manager.merge_paper_data(keep_id, remove_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '论文合并成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '论文合并失败'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'合并失败: {str(e)}'
        })

@app.route('/api/delete-paper/<int:paper_id>', methods=['DELETE'])
def delete_paper(paper_id):
    """API: 删除论文"""
    try:
        conn = sqlite3.connect(paper_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM papers WHERE id = ?', (paper_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({
                'success': True,
                'message': '论文删除成功'
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'message': '论文不存在'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        })


if __name__ == '__main__':
    print("🚀 启动论文管理系统")
    print("📚 请在浏览器中访问: http://localhost:5001")
    print("🔧 使用Ctrl+C停止服务器")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
