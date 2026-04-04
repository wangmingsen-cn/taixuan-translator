# 太玄智译 - 安装指南

本文档详细介绍太玄智译的安装和配置过程。

## 目录
1. [环境要求](#环境要求)
2. [快速安装](#快速安装)
3. [详细配置](#详细配置)
4. [常见问题](#常见问题)
5. [卸载说明](#卸载说明)

---

## 环境要求

### 最低配置
- 操作系统：Windows 10/11 (64位) 或 Linux/Mac
- Python：3.11 或更高版本
- 内存：4GB RAM
- 磁盘空间：2GB（不含 PDF 文件）

### 推荐配置
- 操作系统：Windows 11 (64位)
- Python：3.11.9
- 内存：8GB RAM
- 固态硬盘：10GB 可用空间

---

## 快速安装

### Windows 一键部署

#### 方式 A：使用预打包版本（推荐）
1. 下载 太玄智译v1.0.0-Win64.zip
2. 解压到任意文件夹（如 C:\Program Files\太玄智译）
3. 双击「启动太玄智译.vbs」
4. 等待浏览器自动打开

#### 方式 B：从源码安装

`powershell
# 1. 克隆项目
git clone https://github.com/your-username/taixuan-translator.git
cd taixuan-translator

# 2. 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python -m uvicorn taixuan_translator.api.main:app --reload --port 8000
`

### Linux/Mac 安装

`ash
# 1. 克隆项目
git clone https://github.com/your-username/taixuan-translator.git
cd taixuan-translator

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python -m uvicorn taixuan_translator.api.main:app --reload --port 8000
`

---

## 详细配置

### 1. API 密钥配置

#### 方式一：环境变量（推荐）

`powershell
# Windows PowerShell
 = \"sk-your-deepseek-key-here\"
 = \"sk-your-openai-key-here\"

# Windows CMD
set DEEPSEEK_API_KEY=sk-your-deepseek-key-here
`

`ash
# Linux/Mac
export DEEPSEEK_API_KEY=\"sk-your-deepseek-key-here\"
export OPENAI_API_KEY=\"sk-your-openai-key-here\"
`

#### 方式二：配置文件

复制 .env.example 为 .env 并编辑：

`ash
# 复制示例配置
copy .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
DEEPSEEK_API_KEY=sk-your-key-here
OPENAI_API_KEY=sk-your-key-here
DEEPL_API_KEY=your-deepl-key-here
`

#### 方式三：代码配置（仅开发测试）

编辑 	aixuan_translator/core/config.py：

`python
class DeepSeekSettings(BaseSettings):
    api_key: str = Field(default=\"sk-your-key-here\")
    # ... 其他配置
`

### 2. 支持的翻译引擎

| 引擎 | 环境变量 | 说明 |
|------|----------|------|
| DeepSeek | DEEPSEEK_API_KEY | 默认启用，需要申请 API Key |
| OpenAI | OPENAI_API_KEY | 可选 |
| DeepL | DEEPL_API_KEY | 可选 |
| Claude | CLAUDE_API_KEY | 可选 |
| 千问 | QWEN_API_KEY | 可选 |
| Ollama | OLLAMA_BASE_URL | 本地部署 |

### 3. 获取 API 密钥

#### DeepSeek（推荐）
1. 访问 https://platform.deepseek.com/
2. 注册账号并登录
3. 进入「API Keys」页面
4. 创建新的 API Key
5. 复制并保存（仅显示一次）

#### OpenAI
1. 访问 https://platform.openai.com/
2. 注册账号并登录
3. 进入「API Keys」页面
4. 创建新的 API Key

#### DeepL
1. 访问 https://www.deepl.com/pro-api
2. 注册免费账号
3. 获取 API Key

### 4. 端口配置

默认端口为 8000。如需修改：

`ash
# 命令行指定端口
python -m uvicorn taixuan_translator.api.main:app --port 9000

# 或修改配置
# 编辑 pyproject.toml 中的 \"port\" 配置
`

### 5. 数据库配置

默认使用 SQLite 数据库，存储在：

`
%USERPROFILE%\.taixuan_translator\taixuan.db
`

如需自定义：

`python
# 编辑 config.py
class DatabaseSettings(BaseSettings):
    db_path: str = Field(default=\"%USERPROFILE%/.taixuan_translator/taixuan.db\")
`

---

## 常见问题

### Q1: 启动时提示「端口已被占用」

**解决方案**：
`powershell
# 查看占用端口的进程
netstat -ano | findstr :8000

# 结束占用进程
taskkill /PID <进程ID> /F
`

### Q2: 翻译时提示「API 密钥无效」

**解决方案**：
1. 检查 API 密钥是否正确
2. 确认 API 密钥已激活（部分服务需要激活）
3. 检查账户余额是否充足

### Q3: PDF 解析失败

**解决方案**：
1. 确认 PDF 是文本型（非扫描图片）
2. 尝试用其他软件将 PDF 转为文本
3. 检查 PDF 是否有密码保护

### Q4: 翻译速度慢

**解决方案**：
1. 增加 MAX_WORKERS 并发数
2. 使用缓存避免重复翻译
3. 选择更快的翻译模型

### Q5: 导出 Word 失败

**解决方案**：
1. 确保已安装 python-docx
2. 检查磁盘空间
3. 尝试导出为其他格式

### Q6: 浏览器无法访问

**解决方案**：
1. 检查防火墙设置
2. 确认服务已启动
3. 尝试访问 http://127.0.0.1:8000/health

---

## 卸载说明

### Windows 预打包版本
1. 关闭所有浏览器窗口
2. 结束进程：	aixuan-translator-api.exe
3. 删除安装文件夹

### 从源码安装
`ash
# 退出虚拟环境
deactivate

# 删除项目文件夹
cd ..
rm -rf taixuan-translator

# 或保留虚拟环境以便后续使用
`

---

## 技术支持

- 提交 Issue：https://github.com/your-username/taixuan-translator/issues
- 邮箱：taixuan@studio.example.com

---

*更新时间：2026-04-04*