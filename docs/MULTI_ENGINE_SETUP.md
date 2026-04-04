# 多引擎配置方案

## 支持的翻译引擎

太玄智译支持以下翻译引擎，可根据需求灵活配置：

| 引擎 | 推荐场景 | 性价比 | API Key 获取 |
|------|---------|--------|--------------|
| **DeepSeek** | 默认首选 | ★★★★★ | platform.deepseek.com |
| **OpenAI** | 通用翻译 | ★★★☆☆ | platform.openai.com |
| **Claude** | 学术翻译 | ★★★☆☆ | console.anthropic.com |
| **通义千问** | 中文优化 | ★★★★☆ | dashscope.aliyuncs.com |
| **Gemini** | 多模态 | ★★★☆☆ | aistudio.google.com |
| **MiniMax** | 长文本 | ★★★★☆ | platform.minimaxi.com |
| **Grok** | 快速响应 | ★★★★☆ | console.x.ai |
| **DeepL** | 专业翻译 | ★★☆☆☆ | deepl.com/pro-api |
| **Ollama** | 本地部署 | ★★★★★ | ollama.ai (本地) |

---

## 快速配置（推荐）

### 方案 A：仅使用 DeepSeek（最简单）

```env
TAIXUAN_DEFAULT_ENGINE=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 方案 B：多引擎切换

```env
# 默认引擎
TAIXUAN_DEFAULT_ENGINE=deepseek

# DeepSeek（性价比最高）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI（备选）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Ollama（本地，无需 Key）
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

---

## 详细配置

### DeepSeek 配置

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TEMPERATURE=0.3
DEEPSEEK_TIMEOUT=60
DEEPSEEK_MAX_RETRIES=3
```

**说明**：
- DeepSeek API 价格约为 GPT-4 的 1/10
- 支持 64K 上下文窗口
- 适合大批量学术文档翻译

### OpenAI 配置

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4096
OPENAI_TEMPERATURE=0.3
OPENAI_TIMEOUT=60
OPENAI_MAX_RETRIES=3
```

### Claude 配置

```env
CLAUDE_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLAUDE_BASE_URL=https://api.anthropic.com
CLAUDE_MODEL=claude-3-5-haiku-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_TEMPERATURE=0.3
CLAUDE_TIMEOUT=60
```

### 通义千问配置

```env
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
QWEN_MAX_TOKENS=4096
QWEN_TEMPERATURE=0.3
QWEN_TIMEOUT=60
```

### Ollama 本地配置（无需 API Key）

```env
# Ollama 需先安装：https://ollama.ai/
# 启动服务：ollama serve
# 下载模型：ollama pull qwen2.5:7b

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120
OLLAMA_CONTEXT_WINDOW=8192
```

**优点**：
- 完全免费，无 API 调用费用
- 数据不出网，隐私安全
- 适合内网部署

**缺点**：
- 需要较大内存（7B 模型需 8GB+ RAM）
- 翻译速度取决于硬件配置

### DeepL 配置

```env
DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
DEEPL_API_URL=https://api-free.deepl.com/v2
```

**注意**：DeepL 需要付费订阅，免费 Key 有使用限制

---

## 引擎切换

在 Web UI 中：
1. 打开 "设置" 标签
2. 选择 "翻译引擎" 下拉菜单
3. 选择目标引擎
4. 返回主界面，翻译会自动使用新引擎

通过 API：
```bash
curl -X POST http://127.0.0.1:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"engine": "deepseek", "text": "Hello"}'
```

---

## 性能对比

| 引擎 | 响应速度 | 翻译质量 | 成本 | 备注 |
|------|---------|---------|------|------|
| DeepSeek | 快 | 高 | 低 | 推荐首选 |
| Ollama | 中 | 中 | 无 | 本地部署 |
| OpenAI | 快 | 高 | 中 | 稳定可靠 |
| Claude | 快 | 高 | 中 | 学术友好 |
| 通义千问 | 快 | 高 | 低 | 中文优化 |
| Gemini | 中 | 中 | 中 | 多模态 |
| DeepL | 快 | 高 | 高 | 专业术语 |

---

## 故障排查

### 引擎无法连接

**检查项**：
1. API Key 是否正确
2. 网络是否正常（能否访问对应 API 域名）
3. API Key 是否有余额

**测试命令**：
```bash
# 测试 DeepSeek
curl https://api.deepseek.com/v1/models -H "Authorization: Bearer YOUR_KEY"

# 测试 Ollama
curl http://localhost:11434/api/tags
```

### 翻译超时

**解决**：
- 增大超时时间配置（如 `DEEPSEEK_TIMEOUT=120`）
- 检查网络延迟
- 尝试更换更快的引擎

### 翻译结果不理想

**调整参数**：
- 降低 `TEMPERATURE`（更确定性）
- 增加 `MAX_TOKENS`（更长输出）

---

## 最佳实践

1. **默认 DeepSeek**：性价比最高，适合大部分场景
2. **备用 OpenAI**：配置双引擎，一个出问题可切换
3. **本地 Ollama**：有条件的团队可部署本地模型
4. **术语库积累**：长期使用会积累术语缓存，提高一致性

---

*太玄计算机软件开发工作室 | 2026-04-01*