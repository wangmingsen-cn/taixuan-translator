# 太玄智译 - PDF 翻译工作台

<p align=\"center\">
  <img src=\"https://img.shields.io/badge/Python-3.11+-blue.svg\" alt=\"Python 3.11+\">
  <img src=\"https://img.shields.io/badge/License-MIT-green.svg\" alt=\"License: MIT\">
  <img src=\"https://img.shields.io/badge/Platform-Windows-lightgrey.svg\" alt=\"Platform: Windows\">
</p>

太玄智译是一款专为出版行业设计的 PDF 文档翻译工具，支持一键提取 PDF 文本、智能分段、多引擎翻译（DeepSeek/OpenAI/DeepL/Ollama等），并可导出多种格式的双语对照 Word 文档。

## ✨ 功能特性

### 📄 文档处理
- **PDF 智能解析**：自动提取文本、表格、公式，保留原文格式
- **智能分段**：根据页面结构自动识别段落、标题、脚注
- **双语对照**：支持段落交替、左右分栏、仅译文、脚注模式等多种导出格式

### 🤖 多引擎翻译
| 引擎 | 类型 | 说明 |
|------|------|------|
| DeepSeek | 云端 API | 默认启用，支持中文翻译 |
| OpenAI | 云端 API | GPT-4o / GPT-4o-mini |
| DeepL | 云端 API | 适合英文/德语/法语 |
| Claude | 云端 API | Claude Sonnet 4 |
| Ollama | 本地部署 | 支持 Qwen/Llama 等本地模型 |
| 千问 | 云端 API | 阿里云通义千问 |
| MiniMax | 云端 API | MiniMax 文本模型 |

### 📊 导出格式
- ✅ 段落交替模式（中英段落逐段交替）
- ✅ 左右分栏模式（中文译文对照原文）
- ✅ 纯译文模式（仅中文译文）
- ✅ 脚注模式（原文作为脚注）

### 💡 核心功能
- **翻译缓存**：已翻译段落自动缓存，避免重复调用 API
- **暂停/继续**：支持随时暂停和恢复翻译进度
- **进度显示**：实时显示翻译进度和预估剩余时间
- **API 密钥管理**：支持环境变量或配置文件管理 API Key

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Windows 10/11 (64位)
- 至少 4GB 可用内存

### 安装步骤

#### 1. 克隆仓库
`ash
git clone https://github.com/your-username/taixuan-translator.git
cd taixuan-translator
`

#### 2. 创建虚拟环境（推荐）
`ash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
`

#### 3. 安装依赖
`ash
pip install -r requirements.txt
`

#### 4. 配置 API 密钥

编辑 	aixuan_translator/core/config.py，或在环境变量中设置：

`ash
# DeepSeek（默认启用）
set DEEPSEEK_API_KEY=sk-your-key-here

# OpenAI（可选）
set OPENAI_API_KEY=sk-your-key-here

# DeepL（可选）
set DEEPL_API_KEY=your-key-here
`

#### 5. 启动服务
`ash
# 方式1：直接运行
python -m uvicorn taixuan_translator.api.main:app --reload --port 8000

# 方式2：使用启动脚本
python silent_entry.py
`

#### 6. 访问界面
打开浏览器访问：http://127.0.0.1:8000

## 📖 使用指南

### 1. 上传 PDF
点击上传区域或拖拽 PDF 文件到上传区，支持批量上传。

### 2. 开始翻译
点击「全文翻译」按钮，系统会自动：
- 解析 PDF 提取文本
- 智能分段
- 调用翻译 API
- 实时显示进度

### 3. 导出结果
翻译完成后，选择导出模式：
- 段落交替：适合阅读
- 左右分栏：适合对照
- 纯译文：适合排版
- 脚注模式：适合审校

点击「导出选中版本」即可下载 Word 文档。

## ⚙️ 配置说明

### 配置文件位置
- 主配置：	aixuan_translator/core/config.py
- 环境变量：.env 或系统环境变量
- 示例配置：.env.example

### 主要配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| DEEPSEEK_API_KEY | DeepSeek API 密钥 | （需填写） |
| DEEPSEEK_MODEL | 翻译模型 | deepseek-chat |
| MAX_WORKERS | 并发翻译数 | 3 |
| CACHE_ENABLED | 启用翻译缓存 | true |
| PORT | 服务端口 | 8000 |

## 🏗️ 项目结构

`
taixuan-translator/
├── api/                    # FastAPI 路由
│   ├── main.py            # API 入口
│   ├── routers/           # 路由模块
│   │   ├── upload.py     # 文件上传
│   │   ├── translate.py  # 翻译接口
│   │   ├── export.py     # 导出接口
│   │   └── engines.py    # 引擎管理
│   └── schemas.py         # 数据模型
├── core/                  # 核心模块
│   ├── config.py         # 配置管理
│   ├── utils.py          # 工具函数
│   └── exceptions.py     # 异常定义
├── data/                  # 数据层
│   ├── database.py       # SQLite 数据库
│   ├── cache.py          # 翻译缓存
│   └── models.py         # 数据模型
├── services/              # 业务服务
│   ├── file_parser.py    # PDF 解析
│   ├── export_service.py # 文档导出
│   └── translation_batch.py  # 批量翻译
├── translator/            # 翻译引擎
│   ├── base.py           # 引擎基类
│   ├── deepseek_engine.py
│   ├── openai_engine.py
│   └── factory.py        # 引擎工厂
├── pdf_parser/            # PDF 解析
│   ├── core_parser.py    # 核心解析
│   └── formula_extractor.py  # 公式提取
├── docx_generator/        # Word 生成
│   └── core.py           # 生成器
├── ui/                    # 前端文件
│   ├── web/              # Web 界面
│   │   ├── app.js        # 前端逻辑
│   │   ├── index.html    # 页面模板
│   │   └── styles.css    # 样式
│   └── launcher.py        # 桌面启动器
├── tests/                 # 单元测试
├── scripts/              # 工具脚本
├── main.py               # 主入口
├── silent_entry.py       # 静默启动入口
└── pyproject.toml        # 项目配置
`

## 🔧 开发指南

### 运行测试
`ash
pytest tests/ -v
`

### 代码规范
- 遵循 PEP 8
- 使用 type hints
- 提交前运行 pytest

### 添加新引擎
1. 在 	ranslator/ 目录下创建新的 engine 类
2. 继承 TranslationEngine 基类
3. 实现 	ranslate() 方法
4. 在 actory.py 中注册

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🙏 致谢

- FastAPI - Web 框架
- PyMuPDF - PDF 解析
- python-docx - Word 生成
- DeepSeek - 翻译 API

## 📞 支持

如有问题，请提交 Issue 或联系：294945908@qq.com
