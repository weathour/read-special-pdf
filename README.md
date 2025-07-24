
# PaperReader - 智能学术论文管理系统

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Flask](https://img.shields.io/badge/flask-2.1+-red.svg)

PaperReader 是一个功能强大的学术论文管理生态系统，集成了论文检索、PDF处理、笔记生成和去重管理等多项功能，为研究人员提供了完整的文献管理解决方案。

## 📋 目录

- [主要功能](#-主要功能)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [模块详解](#-模块详解)
- [API 文档](#-api-文档)
- [使用指南](#-使用指南)
- [配置说明](#-配置说明)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)

## 🚀 主要功能

### 核心功能
- **📚 论文管理**: 智能检索、分类管理、去重处理
- **🔍 智能匹配**: 基于DOI、标题、作者的多策略匹配算法
- **📊 统计分析**: 多维度数据统计和可视化展示
- **📄 PDF处理**: PDF文件组织、文本提取、笔记生成
- **🌐 Web界面**: 响应式Web管理界面
- **🔌 浏览器扩展**: Chrome/Firefox扩展，快速论文信息捕获

### 特色功能
- **JSON验证器**: 自动验证和修复论文元数据
- **重复检测**: 基于DOI和标题的智能去重
- **多格式支持**: 支持多种学术数据格式
- **批量处理**: 高效的批量导入和处理能力

## 🏗️ 系统架构

```
PaperReader/
├── paper-management-system/     # 论文管理核心系统
├── pdf-json-checker/           # PDF-JSON检查和组织工具
├── pdf-note-generator/         # PDF笔记生成器
├── browser_extension/          # 浏览器扩展
└── shared/                     # 共享组件和工具
```

### 技术栈
- **后端**: Python 3.8+, Flask, SQLite
- **前端**: HTML5, JavaScript, CSS3, Bootstrap
- **数据处理**: JSON, Pandas, jieba
- **浏览器扩展**: Chrome Extension API
- **文档处理**: PyPDF2, Markdown

## 🎯 快速开始

### 环境要求
- Python 3.8+
- Node.js 14+ (用于浏览器扩展开发)
- SQLite 3

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/weathour/read-special-pdf
cd read-special-pdf
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **初始化数据库**
```bash
cd read-special-pdf/paper-management-system
python paper_manager.py
```

4. **启动系统**
```bash
python run_paper_manager.py
```

5. **访问应用**
打开浏览器访问: http://localhost:5001

## 📦 模块详解

### 1. 论文管理系统 (paper-management-system)

核心的论文管理Web应用，提供完整的论文管理功能。

#### 主要组件
- **`paper_manager.py`**: 核心管理类，处理数据库操作和论文CRUD
- **`paper_matcher.py`**: 智能匹配引擎，支持多策略论文匹配
- **`paper_checker_api.py`**: RESTful API服务，提供程序化访问接口
- **`json_validator.py`**: JSON数据验证和清洗工具

#### Web模板
```
templates/
├── base.html              # 基础模板
├── index.html            # 主页
├── search.html           # 搜索页面
├── paper_detail.html     # 论文详情
├── author_papers.html    # 作者论文列表
├── venue_papers.html     # 期刊论文列表
├── statistics.html       # 统计页面
├── deduplication.html    # 去重管理
└── import.html          # 数据导入
```

### 2. PDF-JSON检查器 (pdf-json-checker)

专门用于PDF文件和JSON元数据的同步和验证。

#### 核心功能
- **`pdf_manager.py`**: PDF文件状态管理和追踪
- **`pdf_organizer.py`**: 智能文件组织和分类
- **`json_validator.py`**: JSON格式验证和修复

#### 使用示例
```python
from pdf_organizer import PDFOrganizer

organizer = PDFOrganizer()
summary = organizer.organize_and_copy("./output")
```

### 3. PDF笔记生成器 (pdf-note-generator)

自动化PDF处理和笔记生成工具。

#### 主要组件
- **`note_generator.py`**: 智能笔记生成引擎
- **`pdf_processor_optimized.py`**: 优化的PDF文本提取
- **`main_optimized.py`**: 主处理流程
- **`app.py`**: Web应用界面

### 4. 浏览器扩展 (browser_extension)

Chrome/Firefox扩展，提供便捷的论文信息采集功能。

#### 文件结构
- **`manifest.json`**: 扩展配置文件
- **`background.js`**: 后台服务脚本
- **`content.js`**: 内容脚本
- **`popup.html/js`**: 扩展弹出界面

## 🔌 API 文档

### 基础API

#### 健康检查
```http
GET /api/health
```

**响应示例:**
```json
{
  "status": "ok",
  "message": "Paper Checker API is running",
  "version": "1.0.0"
}
```

#### 论文检查
```http
POST /api/check-paper
Content-Type: application/json

{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "doi": "10.1000/example",
  "year": "2023"
}
```

**响应示例:**
```json
{
  "found": true,
  "matches": [
    {
      "id": 1,
      "title": "匹配的论文标题",
      "authors": ["作者1", "作者2"],
      "confidence": 0.95,
      "match_method": "doi"
    }
  ],
  "count": 1
}
```

#### 统计信息
```http
GET /api/stats
```

#### 搜索建议
```http
GET /api/search_suggestions?q=机器学习
```

### 高级API

#### 去重管理
```http
POST /api/auto-deduplicate
DELETE /api/delete-paper/<paper_id>
POST /api/merge-papers
```

## 📖 使用指南

### 1. 导入论文数据

#### 通过Web界面导入
1. 访问 `/import` 页面
2. 输入JSON文件夹路径
3. 点击"导入"按钮
4. 查看导入结果和验证报告

#### 通过命令行导入
```bash
cd paper-management-system
python -c "
from paper_manager import PaperManager
pm = PaperManager()
count, failed, report = pm.import_json_folder_with_validation('./json_papers')
print(f'导入成功: {count} 个文件')
"
```

### 2. 论文检索

#### 基础搜索
- 关键词搜索：在搜索框输入关键词
- 高级筛选：按分类、作者、期刊、年份筛选

#### API搜索
```python
import requests

response = requests.post('http://localhost:5001/api/check-paper', 
                        json={'title': '深度学习', 'authors': ['张三']})
print(response.json())
```

### 3. PDF文件管理

#### 组织PDF文件
```bash
cd pdf-json-checker
python run_organizer.py
```

#### 生成处理报告
```bash
python pdf_organizer.py --output-dir ./reports
```

### 4. 笔记生成

#### 批量处理PDF
```bash
cd pdf-note-generator
python main_optimized.py --input-dir ./pdfs --output-dir ./notes
```

#### Web界面处理
1. 访问笔记生成器Web界面
2. 上传PDF文件
3. 选择处理选项
4. 下载生成的笔记

## ⚙️ 配置说明

### 主配置文件 (config.py)

```python
class Config:
    # 数据库配置
    DATABASE_PATH = '../papers.db'
    
    # API配置
    API_HOST = '0.0.0.0'
    API_PORT = 5000
    API_DEBUG = False
    
    # CORS配置
    CORS_ORIGINS = [
        'http://localhost:3000',
        'https://your-domain.com'
    ]
    
    # 文件路径配置
    PDF_FOLDER = './pdfs'
    JSON_FOLDER = './json_papers'
```

### 环境变量
```bash
export PAPERREADER_DB_PATH="/path/to/papers.db"
export PAPERREADER_API_PORT=5001
export PAPERREADER_DEBUG=true
```

## 🛠️ 开发指南

### 本地开发环境搭建

1. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

2. **安装开发依赖**
```bash
pip install -r requirements-dev.txt
```

3. **运行测试**
```bash
python -m pytest tests/
```

### 代码结构约定

- 使用Python PEP 8代码风格
- 函数使用docstring文档
- 类使用类型注解
- 模块级别的日志记录

### 添加新功能

1. 在对应模块中添加功能代码
2. 编写单元测试
3. 更新API文档
4. 提交Pull Request

## ❓ 常见问题

### Q: 数据库初始化失败？
A: 确保SQLite已安装，并检查数据库文件路径权限。

### Q: PDF文件无法访问？
A: 检查PDF文件夹路径配置和文件权限设置。

### Q: 浏览器扩展无法连接API？
A: 确认API服务已启动，检查CORS配置。

### Q: 大量数据导入很慢？
A: 使用批量导入模式，考虑增加数据库索引。

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. **Fork 项目**
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **提交Pull Request**

### 贡献类型
- 🐛 Bug修复
- ✨ 新功能开发
- 📚 文档改进
- 🎨 界面优化
- ⚡ 性能提升

### 开发规范
- 遵循PEP 8代码风格
- 添加适当的测试用例
- 更新相关文档
- 保持向后兼容性


## 👥 团队

- **维护者**: [Yang XJ]

## 🔗 相关链接

- [项目主页](https://github.com/weathour/read-special-pdf)



---

如果您觉得这个项目有用，请给我们一个 ⭐ 星标支持！

如有问题或建议，请提交 [Issue](https://github.com/your-username/PaperReader/issues) 或联系维护者。

