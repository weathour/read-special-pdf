
# Paper Manager Project 全功能使用文档

> 集成：论文库管理系统（paper-management-system）+ PDF/JSON匹配与校验工具（pdf-json-checker）+ 智能PDF笔记生成器（pdf-note-generator）+ 论文在库在线检查API与浏览器插件

---

## 📑 项目结构

```
project-root/
├── paper-management-system/
│   ├── app.py / paper_manager.py
│   ├── templates/...
│   ├── static/...
│   └── ...（核心Web服务、数据库、本地管理）
├── pdf-json-checker/
│   ├── organizer.py / pdf_json_organizer.py
│   └── ...（PDF/JSON文件校验与孤立项检测）
├── pdf-note-generator/
│   ├── main_optimized.py
│   └── ...（AI笔记批量生成与校验）
└── README.md
```

---

## 📦 功能总览

### 1. **论文库管理与检索**（paper-management-system）
- Web界面管理/模糊检索/录入/去重/JSON批量导入/数据库统计等
- 智能导入时自动验证JSON合规性
- 支持基于 DOI/文件名 的查重与去重
- 支持批量/单个论文的详细数据浏览&纠错

### 2. **PDF—JSON校验匹配/文件整理**（pdf-json-checker）
- 批量检测 PDF 是否已被结构化、已入库
- 检出孤立 PDF / 孤立 JSON 文件，支持格式和内容比对
- 支持与数据库 papers.db 自动联动校验（支持模糊匹配、相似度算法）

### 3. **AI智能PDF笔记生成**（pdf-note-generator）
- 批量智能生成 PDF 笔记、结构化摘要
- 支持一次性大批量自动生成+后续二次校验标记

### 4. **在线API+浏览器插件**
- 提供论文查库API（FastAPI/Flask，局域网通用）
- 配套谷歌学术论文在库浏览器插件，自动高亮/统计页面论文在库情况

---

## 🚀 快速开始

### 1. 安装依赖

分别进入三个子模块目录，安装依赖（推荐使用虚拟环境）：

```bash
cd paper-management-system
pip install -r requirements.txt

cd ../pdf-json-checker
pip install -r requirements.txt

cd ../pdf-note-generator
pip install -r requirements.txt
```

如有AI/LLM相关笔记生成功能，请参考 `pdf-note-generator` 子目录下的详细说明。

---

### 2. 启动论文管理系统 Web API

（假定主服务端口为 5001，API端口可自定义）

```bash
# 启动本地论文库管理后台
cd paper-management-system
python app.py   # 或 python paper_manager.py
```

- 默认后台地址：http://localhost:5001
    - 主界面：数据库管理、查重、去重、批量导入、详细查看
    - `/import` 提供批量JSON文件校验、导入与报告
    - `/api/*` 提供自动化论文比对与查库API（供插件/自动化工具调用）

---

### 3. 启动 PDF/JSON 校验器

```bash
cd ../pdf-json-checker
python organizer.py  # 或 python pdf_json_organizer.py
# 按实际文件夹配置 PDF、JSON、数据库路径运行
```
- 主要功能：
    - 检查 PDF 是否有对应 JSON/数据库入库条目
    - 可自动分类「已入库」「孤立PDF」「孤立JSON」
    - 支持详细校验报告导出

---

### 4. 启动笔记生成工具

```bash
cd ../pdf-note-generator
python main_optimized.py
# 批量生成/校验 PDF 笔记或结构摘要
```
- 可根据实际部署LLM/OpenAI Key自定义参数

---

### 5. 启动并安装谷歌学术论文检查插件

**（首次使用建议OpenAPI启动在本机localhost）**

- 依赖 paper-management-system 的 API 服务（假定 5002 端口）
- Chrome/Edge 浏览器进入插件开发者模式，加载
  ```
  paper-management-system/browser_extension/
  ```
  文件夹（详见结构与 manifest.json）
- 浏览器插件将使您在 Google Scholar 实时看到哪些论文已在本地数据库

---

## 🛠️ 常用功能和典型用法

### 1. **论文入库/批量导入（含自动校验）**

- 在 paper-management-system 前端 `/import` 页面
    - 输入JSON文件夹路径，一键完成校验+导入
    - 无效文件自动预警，全部校验日志透明输出

- 支持通过命令行批量校验/整理
    ```bash
    python json_validator.py validate -s ./json_papers/
    python json_validator.py organize -s ./json_papers/ --success ./valid/ --failure ./invalid/
    ```

---

### 2. **PDF与数据库/JSON自动校验整理**

- 检查 PDF 文件、JSON 文件、数据库三方同步
- 检查 API 可用于自动标记未结构化/未入库条目
- 核心脚本可用于周期性内容完整性巡检

---

### 3. **论文查重/去重及DOI管理**

- 内置 “重复DOI” 检查与一键去重功能（跳过 DOI: not available）
- 支持安全预览/确认再去重，查重报告可导出

---

### 4. **浏览器插件论文查库**

**场景**：Google Scholar 打开任意论文列表，自动标记“已在库”“未在库”（高亮、悬浮、统计标识）
- 可在插件弹窗开启/关闭自动查库、查看统计
- 插件与本地 API 配合，无需上传任何隐私数据

**API 支持批量/单篇查询**  
> POST `/api/batch-check`、`/api/check-paper`

---

### 5. **AI批量笔记与摘要生成**

- 通过pdf-note-generator批量调用本地/云端大模型，一次性生成所有论文笔记/摘要
- 支持校验与标签自动补充

---

## 📊 典型工作流

1. 新论文、旧论文批量收集
2. 用pdf-json-checker检查孤立PDF/JSON，整理到标准格式
3. 用 `/import` 页面批量将JSON导入数据库（校验后自动跳过不合规文件）
4. 数据库提供综合论文管理、查重、去重、批量导出、统计
5. 浏览器插件实时检测/标记谷歌学术页面的论文在库情况
6. 可用AI工具生成或补齐论文笔记/结构化摘要

---

## 🎨 基本界面效果

- **论文库管理 Web**：一站式统一论文管理、查重、导入、统计、查库、批量编辑
- **PDF/JSON校验**：孤立项报表、可视化匹配结果
- **谷歌学术插件**：高亮标注、实时统计、查库结果一目了然
- **AI笔记**：批量智能生成笔记/提要/核心要点

---

## 📚 FAQ & 技术支持

- **跨系统兼容**：推荐 Python 3.8-3.12，Win/Linux/Mac 通用
- **批量导入遇到JSON格式报错？** 请先用 pdf-json-checker 或 json_validator 脚本校验
- **孤立PDF/JSON怎么同步？** 用 organizer 或 Web前端“数据同步”部分
- **API/插件无法联通？** 请确保 paper-management-system API 已经本地运行，且端口开放

---

## ⏳ 未来可扩展方向

- 支持多用户/远程同步/云端论文查重接口
- GROBID、CrossRef等外部数据自动补全
- 更丰富的AI工具链支持

---

## 💡 联系与贡献

欢迎PR、issue、功能建议！  
- 核心仓库负责人：[mr.weathour@gmail.com]
- 文档完善与部署说明欢迎反馈和补充


