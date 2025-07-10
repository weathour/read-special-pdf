import hashlib
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class FileManager:
    """文件管理器 - 处理重复检测和历史记录"""

    def __init__(self, db_path: str = "processed_files.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_hash TEXT NOT NULL UNIQUE,
                    file_size INTEGER NOT NULL,
                    processed_at TIMESTAMP NOT NULL,
                    output_md_path TEXT,
                    output_json_path TEXT,
                    processing_time REAL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    config_hash TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON processed_files(file_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_path ON processed_files(file_path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_files(processed_at)')
            conn.commit()

    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """计算文件MD5哈希"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"❌ 计算文件哈希失败: {e}")
            return None

    def calculate_config_hash(self, config: dict) -> str:
        """计算配置哈希（用于检测配置变化）"""
        relevant_config = {
            'prompts': config.get('prompts', {}),
            'processing': config.get('processing', {}),
            'api_model': config.get('api', {}).get('model', '')
        }
        config_str = json.dumps(relevant_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def is_file_processed(self, file_path: Path, config_hash: str) -> Optional[Dict]:
        """检查文件是否已处理"""
        file_hash = self.calculate_file_hash(file_path)
        if not file_hash:
            return None
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM processed_files 
                WHERE file_hash = ? AND success = 1
                ORDER BY processed_at DESC
                LIMIT 1
            ''', (file_hash,))
            result = cursor.fetchone()
        if result:
            record = {
                'id': result[0],
                'file_path': result[1],
                'file_name': result[2],
                'file_hash': result[3],
                'file_size': result[4],
                'processed_at': result[5],
                'output_md_path': result[6],
                'output_json_path': result[7],
                'processing_time': result[8],
                'success': result[9],
                'error_message': result[10],
                'config_hash': result[11]
            }
            record['config_changed'] = (record['config_hash'] != config_hash)
            if record['config_changed']:
                print(f"⚠️  配置已变化，建议重新处理: {file_path.name}")
            return record
        return None

    def record_processing(self, file_path: Path, config_hash: str, 
                         output_md_path: Optional[Path] = None, 
                         output_json_path: Optional[Path] = None,
                         processing_time: float = 0.0,
                         success: bool = True,
                         error_message: str = None):
        """记录处理结果"""
        file_hash = self.calculate_file_hash(file_path)
        if not file_hash:
            return
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO processed_files 
                    (file_path, file_name, file_hash, file_size, processed_at, 
                     output_md_path, output_json_path, processing_time, success, 
                     error_message, config_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(file_path),
                    file_path.name,
                    file_hash,
                    file_path.stat().st_size,
                    datetime.now().isoformat(),
                    str(output_md_path) if output_md_path else None,
                    str(output_json_path) if output_json_path else None,
                    processing_time,
                    success,
                    error_message,
                    config_hash
                ))
        except sqlite3.IntegrityError:
            print(f"⚠️ 记录已存在，跳过：{file_path.name}")

    def get_processing_history(self, limit: int = 50) -> List[Dict]:
        """获取处理历史"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM processed_files 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (limit,))
            results = cursor.fetchall()
        history = []
        for result in results:
            history.append({
                'id': result[0],
                'file_path': result[1],
                'file_name': result[2],
                'file_hash': result[3],
                'file_size': result[4],
                'processed_at': result[5],
                'output_md_path': result[6],
                'output_json_path': result[7],
                'processing_time': result[8],
                'success': result[9],
                'error_message': result[10],
                'config_hash': result[11]
            })
        return history

    def remove_processing_record(self, file_hash: str):
        """移除处理记录（用于强制重处理）"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processed_files WHERE file_hash = ?', (file_hash,))
            conn.commit()

    def get_duplicate_files(self) -> List[Dict]:
        """获取重复文件列表"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_hash, COUNT(*) as count, 
                       GROUP_CONCAT(file_path) as paths,
                       GROUP_CONCAT(processed_at) as dates
                FROM processed_files 
                WHERE success = 1
                GROUP BY file_hash 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            ''')
            results = cursor.fetchall()
        duplicates = []
        for result in results:
            duplicates.append({
                'file_hash': result[0],
                'count': result[1],
                'paths': result[2].split(','),
                'dates': result[3].split(',')
            })
        return duplicates

    def cleanup_old_records(self, days: int = 30):
        """清理旧记录"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM processed_files 
                WHERE processed_at < ? AND success = 0
            ''', (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()
        return deleted_count

    def export_history(self, output_path: Path):
        """导出处理历史"""
        history = self.get_processing_history(limit=1000)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"✅ 处理历史已导出到: {output_path}")

    def get_statistics(self) -> Dict:
        """获取处理统计"""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM processed_files')
            total_processed = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM processed_files WHERE success = 1')
            successful_processed = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM processed_files WHERE success = 0')
            failed_processed = cursor.fetchone()[0]
            cursor.execute('SELECT SUM(processing_time) FROM processed_files WHERE success = 1')
            total_time = cursor.fetchone()[0] or 0
            cursor.execute('SELECT AVG(processing_time) FROM processed_files WHERE success = 1')
            avg_time = cursor.fetchone()[0] or 0
            cursor.execute('SELECT MAX(processed_at) FROM processed_files')
            last_processed = cursor.fetchone()[0]
        return {
            'total_processed': total_processed,
            'successful_processed': successful_processed,
            'failed_processed': failed_processed,
            'success_rate': (successful_processed / total_processed * 100) if total_processed > 0 else 0,
            'total_time': total_time,
            'avg_time': avg_time,
            'last_processed': last_processed
        }