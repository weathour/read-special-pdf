
# config.py
import os

class Config:
    # 数据库配置
    DATABASE_PATH = 'papers.db'  # 修改为 papers.db
    
    # API配置
    API_HOST = '0.0.0.0'
    API_PORT = 5002
    API_DEBUG = True
    
    # 匹配算法配置
    MATCH_THRESHOLD = 0.8
    
    # 支持的匹配方式
    MATCH_METHODS = {
        'doi': {'weight': 1.0, 'enabled': True},
        'title': {'weight': 0.8, 'enabled': True},
        'author_title': {'weight': 0.7, 'enabled': True},
        'fuzzy_title': {'weight': 0.6, 'enabled': True}
    }
    
    # CORS配置
    CORS_ORIGINS = [
        'https://scholar.google.com',
        'https://scholar.google.com.hk',
        'https://scholar.google.cn',
        'http://localhost:3000',
        'chrome-extension://*'
    ]
