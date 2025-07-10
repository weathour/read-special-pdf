
# PDF 智能笔记与论文管理系统

一个集成的学术论文处理工具集，包含 PDF 智能摘要生成和论文数据库管理两大核心功能。

## ✨ 项目概述

本项目包含两个相互配合的子系统：

### 📖 PDF 智能笔记生成器 (`pdf-note-generator/`)
- **智能摘要**：自动提取 PDF 论文的关键信息
- **多格式输出**：支持 JSON、Markdown、TXT 格式
- **批量处理**：支持批量上传和处理多个 PDF
- **实时进度**：Web 界面显示处理进度
- **结构化分析**：自动提取摘要、方法、结论等关键部分

### 🗂️ 论文数据库管理系统 (`paper-management-system/`)
- **智能检索**：支持标题、作者、关键词、期刊等多维度搜索
- **统计分析**：可视化展示论文分布、年份趋势、期刊统计
- **数据导入**：批量导入 JSON 格式的论文数据
- **美观展示**：结构化展示论文详细信息和分析内容
- **作者分析**：按作者查看相关论文

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd read-special-pdf
```

### 2. 一键环境配置
```bash
# 创建统一的虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装所有依赖
pip install -r requirements.txt
```

### 3. 启动服务

#### 方式一：使用便捷脚本（推荐）
```bash
# 启动 PDF 智能笔记生成器
./start_pdf_generator.sh

# 启动论文数据库管理系统
./start_paper_manager.sh
```

#### 方式二：手动启动
```bash
# 启动 PDF 智能笔记生成器
source venv/bin/activate
cd pdf-note-generator
python app.py
# 访问：http://localhost:5000

# 启动论文数据库管理系统（新终端）
source venv/bin/activate
cd paper-management-system
python run_paper_manager.py
# 访问：http://localhost:5001
```

## 📝 使用流程

### 完整工作流程
```
PDF 文件 → PDF生成器 → JSON数据 → 论文管理系统 → 检索分析
```

### 详细步骤
1. **PDF 上传** → 在 PDF 生成器中上传论文 PDF
2. **智能分析** → 自动提取摘要、方法、结论等
3. **生成数据** → 输出 JSON 格式的结构化数据
4. **导入管理** → 将 JSON 数据导入论文管理系统
5. **检索分析** → 使用管理系统进行检索和统计分析

### PDF 智能笔记生成器使用
1. 访问 http://localhost:5000
2. 上传单个或多个 PDF 文件
3. 选择输出格式（JSON/Markdown/TXT）
4. 点击开始处理，查看实时进度
5. 下载生成的笔记文件

### 论文数据库管理系统使用
1. 访问 http://localhost:5001
2. 在导入页面选择 PDF 生成器产生的 JSON 文件
3. 批量导入到数据库中
4. 使用搜索功能查找特定论文
5. 查看详细的论文信息和分析内容
6. 使用统计功能分析论文分布

## 🔄 数据流转

两个系统通过 JSON 文件进行数据交换：

- **PDF 生成器输出**：`pdf-note-generator/web_outputs/`
- **论文管理系统导入**：可直接读取上述目录的 JSON 文件

## 🛠️ 技术栈

- **后端**：Python Flask
- **前端**：HTML5, CSS3, JavaScript, Bootstrap
- **数据库**：SQLite
- **PDF 处理**：PyMuPDF, pdfplumber
- **AI 集成**：支持多种 AI API

## 📊 功能特色

### PDF 智能笔记生成器
- ✅ 自动提取论文结构化信息
- ✅ 支持批量处理
- ✅ 多格式输出（JSON/Markdown/TXT）
- ✅ 实时处理进度显示
- ✅ Web 界面友好

### 论文数据库管理系统
- ✅ 多维度搜索（标题、作者、关键词、期刊）
- ✅ 统计分析和可视化
- ✅ 美观的论文详情展示
- ✅ 作者和期刊分析
- ✅ 批量数据导入

## 🔧 开发说明

### 项目结构
```
read-special-pdf/
├── venv/                      # 统一的虚拟环境
├── requirements.txt           # 统一的依赖文件
├── pdf-note-generator/        # PDF智能笔记生成器
│   ├── app.py                # Web应用主程序
│   ├── pdf_processor.py      # PDF处理逻辑
│   ├── templates/            # Web模板
│   └── web_outputs/          # 生成的JSON文件
├── paper-management-system/   # 论文数据库管理系统
│   ├── paper_manager.py      # 主程序
│   ├── templates/            # Web模板
│   └── json_papers/          # 导入的JSON文件
├── .gitignore               # Git忽略文件
└── README.md               # 项目说明
```

### 环境管理
- 使用统一的虚拟环境，避免依赖冲突
- 所有依赖都在 `requirements.txt` 中定义
- 两个子系统共享相同的 Python 包

## 🚨 注意事项

1. **端口冲突**：两个系统默认使用不同端口（5000 和 5001）
2. **数据路径**：确保 JSON 文件路径正确配置
3. **虚拟环境**：始终在激活虚拟环境的状态下运行
4. **依赖更新**：如需添加新依赖，请更新 `requirements.txt`

## 🔧 故障排除

### 常见问题

**Q: 启动时提示模块找不到**
```bash
# 确保虚拟环境已激活
source venv/bin/activate
pip install -r requirements.txt
```

**Q: 端口被占用**
```bash
# 查看端口占用
netstat -tulpn | grep :5000
# 或修改代码中的端口配置
```

**Q: PDF 处理失败**
- 确保 PDF 文件不是扫描版（纯图片）
- 检查 PDF 文件是否损坏
- 确认文件路径正确

## 📊 数据安全

- **本地处理**：所有数据处理在本地完成
- **隐私保护**：不会上传个人文档到云端
- **数据备份**：建议定期备份数据库和生成的文件

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交变更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

## 📞 联系方式

如有问题或建议，请通过 Issues 或 Pull Request 与我们联系。

---

## 🎯 快速上手指南

### 第一次使用
1. `git clone` 项目
2. `python3 -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `./start_pdf_generator.sh` 或 `./start_paper_manager.sh`

### 日常使用
1. `source venv/bin/activate`
2. 启动所需的服务
3. 在浏览器中访问对应地址

就这么简单！🚀

 
