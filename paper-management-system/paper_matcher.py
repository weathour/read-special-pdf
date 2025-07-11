
# paper_matcher.py
import sqlite3
import json
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple
from config import Config

class PaperMatcher:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.config = Config()
    
    def normalize_title(self, title: str) -> str:
        """标准化标题：去除特殊字符，转小写"""
        if not title:
            return ""
        # 移除标点符号，转小写
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        # 移除多余空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def normalize_author(self, author: str) -> str:
        """标准化作者名：只保留字母"""
        if not author:
            return ""
        return re.sub(r'[^a-zA-Z\s]', '', author.lower()).strip()
    
    def similarity_score(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1, text2).ratio()
    
    def match_by_doi(self, doi: str) -> Optional[Dict]:
        """通过DOI精确匹配"""
        if not doi:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title_cn, title_en, authors, venue, publication_year, file_name
            FROM papers 
            WHERE doi = ? AND doi != "" AND doi IS NOT NULL
        ''', (doi,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'title_cn': result[1],
                'title_en': result[2],
                'authors': json.loads(result[3]) if result[3] else [],
                'venue': result[4],
                'publication_year': result[5],
                'file_name': result[6],
                'match_method': 'doi',
                'confidence': 1.0
            }
        return None
    
    def match_by_title(self, title: str, threshold: float = 0.9) -> List[Dict]:
        """通过标题匹配"""
        if not title:
            return []
        
        normalized_title = self.normalize_title(title)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title_cn, title_en, authors, venue, publication_year, file_name
            FROM papers 
            WHERE title_en != "" AND title_en IS NOT NULL
        ''')
        
        results = []
        for row in cursor.fetchall():
            db_title = self.normalize_title(row[2])  # title_en
            similarity = self.similarity_score(normalized_title, db_title)
            
            if similarity >= threshold:
                results.append({
                    'id': row[0],
                    'title_cn': row[1],
                    'title_en': row[2],
                    'authors': json.loads(row[3]) if row[3] else [],
                    'venue': row[4],
                    'publication_year': row[5],
                    'file_name': row[6],
                    'match_method': 'title',
                    'confidence': similarity
                })
        
        conn.close()
        return sorted(results, key=lambda x: x['confidence'], reverse=True)
    
    def match_by_author_title(self, title: str, authors: List[str], year: str = None) -> List[Dict]:
        """通过作者+标题组合匹配"""
        if not title or not authors:
            return []
        
        normalized_title = self.normalize_title(title)
        normalized_authors = [self.normalize_author(author) for author in authors]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        if year:
            cursor.execute('''
                SELECT id, title_cn, title_en, authors, venue, publication_year, file_name
                FROM papers 
                WHERE publication_year = ? AND title_en != "" AND title_en IS NOT NULL
            ''', (year,))
        else:
            cursor.execute('''
                SELECT id, title_cn, title_en, authors, venue, publication_year, file_name
                FROM papers 
                WHERE title_en != "" AND title_en IS NOT NULL
            ''')
        
        results = []
        for row in cursor.fetchall():
            db_title = self.normalize_title(row[2])
            db_authors = json.loads(row[3]) if row[3] else []
            
            # 计算标题相似度
            title_similarity = self.similarity_score(normalized_title, db_title)
            
            # 计算作者相似度
            author_similarity = 0.0
            if db_authors:
                db_authors_normalized = [self.normalize_author(author) for author in db_authors]
                max_author_sim = 0.0
                for norm_author in normalized_authors:
                    for db_author in db_authors_normalized:
                        sim = self.similarity_score(norm_author, db_author)
                        max_author_sim = max(max_author_sim, sim)
                author_similarity = max_author_sim
            
            # 综合相似度
            combined_similarity = (title_similarity * 0.7 + author_similarity * 0.3)
            
            if combined_similarity >= 0.6:
                results.append({
                    'id': row[0],
                    'title_cn': row[1],
                    'title_en': row[2],
                    'authors': db_authors,
                    'venue': row[4],
                    'publication_year': row[5],
                    'file_name': row[6],
                    'match_method': 'author_title',
                    'confidence': combined_similarity
                })
        
        conn.close()
        return sorted(results, key=lambda x: x['confidence'], reverse=True)
    
    def search_papers(self, query: Dict) -> List[Dict]:
        """主要搜索接口"""
        results = []
        
        # 1. 尝试DOI匹配（最高优先级）
        if query.get('doi'):
            doi_match = self.match_by_doi(query['doi'])
            if doi_match:
                return [doi_match]
        
        # 2. 标题匹配
        if query.get('title'):
            title_matches = self.match_by_title(query['title'], threshold=0.85)
            results.extend(title_matches)
        
        # 3. 作者+标题匹配
        if query.get('title') and query.get('authors'):
            author_title_matches = self.match_by_author_title(
                query['title'], 
                query['authors'], 
                query.get('year')
            )
            results.extend(author_title_matches)
        
        # 去重并排序
        seen_ids = set()
        unique_results = []
        for result in sorted(results, key=lambda x: x['confidence'], reverse=True):
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                unique_results.append(result)
        
        return unique_results[:5]  # 返回最相关的5个结果
