
# paper_checker_api.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
import sys
import traceback

# 尝试导入自定义模块
try:
    from paper_matcher import PaperMatcher
    from config import Config
    print("✅ 成功导入自定义模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置CORS
CORS(app, origins=Config.CORS_ORIGINS, methods=['GET', 'POST', 'OPTIONS'])

# 初始化匹配器
try:
    matcher = PaperMatcher()
    print("✅ 成功初始化论文匹配器")
except Exception as e:
    print(f"❌ 初始化匹配器失败: {e}")
    traceback.print_exc()
    sys.exit(1)

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    logger.info("健康检查请求")
    return jsonify({
        'status': 'ok',
        'message': 'Paper Checker API is running',
        'version': '1.0.0',
        'port': Config.API_PORT
    })

@app.route('/api/check-paper', methods=['POST', 'OPTIONS'])
def check_paper():
    """检查论文是否在数据库中"""
    if request.method == 'OPTIONS':
        # 处理预检请求
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No JSON data provided'
            }), 400
        
        # 提取查询信息
        query = {
            'title': data.get('title', ''),
            'authors': data.get('authors', []),
            'doi': data.get('doi', ''),
            'year': data.get('year', ''),
            'venue': data.get('venue', '')
        }
        
        logger.info(f"检查论文: {query.get('title', 'No title')[:50]}...")
        
        # 搜索匹配的论文
        matches = matcher.search_papers(query)
        
        if matches:
            logger.info(f"找到 {len(matches)} 个匹配结果")
            return jsonify({
                'found': True,
                'matches': matches,
                'count': len(matches),
                'query': query
            })
        else:
            logger.info("未找到匹配的论文")
            return jsonify({
                'found': False,
                'matches': [],
                'count': 0,
                'query': query
            })
    
    except Exception as e:
        logger.error(f"检查论文时出错: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取数据库统计信息"""
    try:
        import sqlite3
        
        conn = sqlite3.connect(Config.DATABASE_PATH)  # 这里已经使用Config.DATABASE_PATH
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM papers')
        total_papers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND doi != ""')
        papers_with_doi = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT publication_year) FROM papers WHERE publication_year IS NOT NULL')
        unique_years = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_papers': total_papers,
            'papers_with_doi': papers_with_doi,
            'unique_years': unique_years,
            'api_version': '1.0.0',
            'database_path': Config.DATABASE_PATH
        })
    
    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test_api():
    """测试API连接"""
    try:
        # 测试数据库连接
        import sqlite3
        conn = sqlite3.connect(Config.DATABASE_PATH)  # 这里已经使用Config.DATABASE_PATH
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM papers')
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'message': 'API测试成功',
            'database_connected': True,
            'total_papers': count,
            'database_path': Config.DATABASE_PATH
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'API测试失败: {str(e)}',
            'database_connected': False
        }), 500


if __name__ == '__main__':
    print("🚀 启动论文检查器API...")
    print(f"📊 数据库路径: {Config.DATABASE_PATH}")
    print(f"🌐 API地址: http://localhost:{Config.API_PORT}")
    print(f"🔍 健康检查: http://localhost:{Config.API_PORT}/api/health")
    
    try:
        app.run(
            host=Config.API_HOST,
            port=Config.API_PORT,
            debug=Config.API_DEBUG
        )
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        traceback.print_exc()
