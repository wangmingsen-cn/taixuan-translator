# 太玄智译 - 详细安装配置指南

## 目录

1. [环境要求](#环境要求)
2. [安装步骤](#安装步骤)
3. [配置翻译引擎](#配置翻译引擎)
4. [验证安装](#验证安装)
5. [常见问题](#常见问题)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 x64 |
| 内存 | ≥ 4 GB |
| 硬盘 | ≥ 500 MB 可用空间 |
| 网络 | 互联网连接（翻译 API 调用） |

---

## 安装步骤

### 步骤 1：解压

右键 `taixuan-translator-v1.0.0-win64.zip` → "全部解压" → 选择目标路径（如 `D:\太玄智译`）

### 步骤 2：配置环境变量（可选）

将以下路径添加到系统 PATH：
```
D:\太玄智译\app
```

### 步骤 3：配置 API Key

1. 进入安装目录
2. 复制 `.env.example` 为 `.env`
3. 用记事本/VS Code 打开 `.env`
4. 找到对应引擎的 API Key 填写区域
5. 保存文件

### 步骤 4：启动服务

**方式 A（推荐）**：
- 双击 `启动服务.bat`

**方式 B（手动）**：
```cmd
cd app
taixuan-translator-api.exe --host 127.0.0.1 --port 8000
```

### 步骤 5：访问

浏览器打开 `http://127.0.0.1:8000`

---

## 配置翻译引擎

### DeepSeek（推荐，性价比高）

1. 访问 https://platform.deepseek.com/
2. 注册/登录 → "API Keys" → 创建 Key
3. 在 `.env` 中填写：
```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
TAIXUAN_DEFAULT_ENGINE=deepseek
```

### OpenAI

1. 访问 https://platform.openai.com/
2. 注册/登录 → "API Keys" → 创建 Key
3. 在 `.env` 中填写：
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
TAIXUAN_DEFAULT_ENGINE=openai
```

### 通义千问

1. 访问 https://dashscope.aliyuncs.com/
2. 注册/登录 → "API-KEY 管理" → 创建 Key
3. 在 `.env` 中填写：
```env
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
TAIXUAN_DEFAULT_ENGINE=qwen
```

### Ollama（本地模型，无需 Key）

1. 下载安装：https://ollama.ai/
2. 启动 Ollama：`ollama serve`
3. 下载模型：`ollama pull qwen2.5:7b`
4. 在 `.env` 中填写：
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
TAIXUAN_DEFAULT_ENGINE=ollama
```

---

## 验证安装

### 1. 服务启动验证

启动服务后，命令行应显示：
```
太玄智译 API 服务启动中...
[太玄智译] API 服务已启动
```

### 2. 浏览器访问

访问 http://127.0.0.1:8000 应显示太玄智译界面

### 3. API 文档

访问 http://127.0.0.1:8000/docs 可查看 Swagger API 文档

### 4. 健康检查

访问 http://127.0.0.1:8000/health 返回：
```json
{"success": true, "data": {"service": "ok", "database": {...}}}
```

---

## 常见问题

### Q1: 双击启动后闪退

**原因**：缺少 API Key  
**解决**：确保 `.env` 文件存在且包含有效的 API Key

### Q2: SmartScreen 警告

**原因**：代码签名证书未申请  
**解决**：点击"更多信息"→"仍要运行"，或等待 v1.0.1 更新

### Q3: 翻译失败

**检查项**：
1. `.env` 中 API Key 是否正确
2. 网络是否正常
3. API Key 是否有余额

### Q4: 端口被占用

**解决**：
```cmd
# 查找占用进程
netstat -ano | findstr 8000

# 结束进程（假设 PID 是 1234）
taskkill /PID 1234 /F
```

### Q5: 数据库初始化失败

**解决**：删除 `C:\Users\<用户名>\.taixuan_translator\` 目录，重新启动

---

## 卸载

1. 停止服务（关闭命令行窗口）
2. 删除安装目录
3. （可选）删除数据目录 `C:\Users\<用户名>\.taixuan_translator\`

---

## 数据位置

| 数据类型 | 路径 |
|----------|------|
| 数据库 | `C:\Users\<用户名>\.taixuan_translator\taixuan.db` |
| 日志 | `C:\Users\<用户名>\.taixuan_translator\logs\` |
| 导出文件 | `C:\Users\<用户名>\.taixuan_translator\exports\` |

---

*太玄计算机软件开发工作室 | 2026-04-01*