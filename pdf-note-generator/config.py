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
        "extraction_prompt": "Please extract key information from the following academic paper and provide a detailed structured analysis, outputting only in strict JSON format (do not include any additional explanatory text):\n\nReturn your answer in the following JSON structure:\n\n{\n    \"title_cn\": \"Chinese title of the paper (translate if not available)\",\n    \"title_en\": \"English title of the paper\",\n    \"category\": \"Paper category (e.g., Machine Learning, Computer Vision, Natural Language Processing, etc.)\",\n    \"topics\": [\"Topic 1\", \"Topic 2\", \"Topic 3\"],\n    \"keywords\": [\"Keyword 1\", \"Keyword 2\", \"Keyword 3\"],\n    \"abstract\": \"Abstract of the paper, the same as the original abstract\",\n    \"methodology\": \"Main research methods\",\n    \"conclusion\": \"Main conclusions\",\n    \"authors\": [\"Author 1\", \"Author 2\"],\n    \"publication_year\": \"Publication year\",\n    \"venue\": \"Publication conference or journal\",\n    \"doi\": \"DOI (if available)\",\n    \"bibtex_citation\": \"BibTeX citation name in the format {authors}_{shorttitle}_{year}\",\n    \"analysis\": {\n        \"Overview\": \"Briefly summarize the main content and research area of the paper.\",\n        \"Background_and_Motivation\": [\n            \"Describe the research background and broader challenges addressed by the paper.\",\n            \"Explain the research motivation and specific problems to be solved.\",\n            \"Analyze how the authors argue for the necessity and urgency of the research problem.\",\n            \"Describe how the authors relate the specific problem to the broader challenge and establish its significance.\",\n            \"Specify the disciplines or interdisciplinary fields to which this paper contributes.\"\n        ],\n        \"Conceptual_Framework_and_Innovations\": [\n            \"List the 2-3 core concepts of the paper and their definitions.\",\n            \"Analyze the logical relationship network among these concepts.\",\n            \"Describe key (including implicit) assumptions underlying the research.\",\n            \"Evaluate the type of contribution the paper makes to the knowledge system of its field.\"\n        ],\n        \"Methodology\": [\n            \"Describe the core research methods and technical approaches used.\",\n            \"Analyze the novelty, applicability, and rationality of the methodology.\",\n            \"Describe data sources, characteristics, preprocessing steps, and evaluate their representativeness.\",\n            \"Analyze the rigor of experimental design and adequacy of evaluation metrics.\",\n            \"Discuss whether the research follows a specific theoretical paradigm or school, and how this affects the research perspective.\"\n        ],\n        \"Results\": [\n            \"Summarize key experimental results.\",\n            \"Analyze the significance, reliability, and stability of the results.\"\n        ],\n        \"Argumentation_and_Logic\": [\n            \"Describe the overall structure of the authors' argument.\",\n            \"List key steps and logical links in the argumentation.\",\n            \"Analyze strengths and weaknesses of the reasoning and how the authors address potential rebuttals.\"\n        ],\n        \"Strengths_and_Limitations\": [\n            \"Summarize the strengths and innovations of the paper.\",\n            \"Analyze the boundaries and limitations of the methodology.\",\n            \"Discuss how the choice of theoretical paradigm constrains the conclusions.\"\n        ],\n        \"Academic_Discourse_and_Rhetoric\": [\n            \"Analyze the role of the paper within the disciplinary discourse.\",\n            \"Describe the specific terminology, tone, and rhetorical strategies used by the authors.\",\n            \"Evaluate how the authors build authority through citations and their underlying motivations.\"\n        ],\n        \"Conclusions_and_Implications\": [\n            \"Summarize the main conclusions.\",\n            \"Provide insights and suggestions for future research.\"\n        ]\n    }\n}\n\nWhen generating the bibtex_citation field:\n- Use the last name of the first author for {authors}.\n- Use the first word of the English title for {shorttitle} (if it is a hyphenated word, use the whole hyphenated word).\n- Use the publication year for {year}, or \"nodate\" if the year is not available.\n\nBase your extraction and analysis solely on the following paper content:\n{text}"
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

