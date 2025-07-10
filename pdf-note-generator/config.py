# config.py - 配置管理模块
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "api": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-167c209e92854627864c887ff8f7fd1a",
        "model": "deepseek-chat",
        "timeout": 30,
        "max_retries": 3
    },
    "prompts": {
        "analysis_prompt": "请分析以下论文内容，提供详细的分析报告",
        "extraction_prompt": "请从以下论文中提取关键信息"
    },
    "output": {
        "md_template": "detailed_analysis",
        "json_fields": ["title_cn", "title_en", "category", "topics", "keywords", "abstract", "methodology", "conclusion"]
    },
    "processing": {
        "max_pages": 50,
        "chunk_size": 4000
    }
}

def load_config(config_path):
    """加载配置文件"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"配置文件 {config_path} 不存在，创建默认配置")
        save_config(config_path, DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 合并默认配置（防止缺少字段）
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG

def save_config(config_path, config):
    """保存配置文件"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"配置文件已保存到: {config_path}")
    except Exception as e:
        print(f"保存配置文件失败: {e}")

def update_api_key(config_path, new_api_key):
    """更新API密钥"""
    config = load_config(config_path)
    config['api']['api_key'] = new_api_key
    save_config(config_path, config)

def update_prompts(config_path, new_prompts):
    """更新提示词"""
    config = load_config(config_path)
    config['prompts'].update(new_prompts)
    save_config(config_path, config)

