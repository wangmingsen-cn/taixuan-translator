# 🎨 太玄智译 - UI视觉设计优化交接文档

**交接人：** 高级前端工程师  
**接收人：** 高级UI设计师  
**日期：** 2026-03-30  
**项目：** 太玄智译 PDF智能翻译系统

---

## 📋 项目概述

太玄智译是一款面向学术/技术文档的PDF精准翻译工具，支持：
- 多种文件格式解析（PDF/DOCX/ePub/HTML/TXT）
- 多引擎翻译（DeepSeek/Claude/千问/Minimax/Ollama/OpenAI）
- 双语对照导出（Word出版标准）

**当前状态：** 功能开发完成，前端页面基础样式已实现，待UI设计师优化视觉效果。

---

## 📁 交付文件清单

| 文件路径 | 说明 | 行数 |
|----------|------|------|
| `ui/web/index.html` | 主界面HTML结构 | ~450行 |
| `ui/web/styles.css` | 样式表（深色主题） | ~850行 |
| `ui/web/app.js` | 前端交互逻辑 | ~700行 |

**文件位置：**  
`C:\Users\29494\.qclaw\workspace\taixuan_translator\ui\web\`

---

## 🎯 UI优化任务清单

### 1️⃣ 整体视觉风格优化

#### 当前状态
- 基础深色主题已实现
- 使用CSS变量管理配色
- 响应式布局支持

#### 需优化项
- [ ] **配色方案细化**：当前主色 `#2563eb` 偏普通，建议调研金融/科技类SaaS产品配色
- [ ] **字体层级**：统一标题/正文/注释的字体大小和权重
- [ ] **间距系统**：建立8px为基础的 spacing scale
- [ ] **阴影/层次**：增加卡片层级感，优化阴影参数

### 2️⃣ 上传面板优化

#### 当前状态
```
┌─────────────────────────────┐
│      📄 拖拽文件到此处      │
│    或点击选择文件            │
│        [选择文件]           │
└─────────────────────────────┘
```

#### 优化建议
- [ ] 增加文件类型图标（PDF/DOCX/ePub各不同）
- [ ] 添加热门文件格式提示徽章
- [ ] 拖拽时的动效反馈（光晕、波纹）
- [ ] 上传进度动画优化

### 3️⃣ 翻译控制台优化

#### 当前状态
- 左右分栏布局
- 章节导航侧边栏
- 底部进度条

#### 需优化项
- [ ] **段落对比展示**：原文与译文采用不同背景色区分
- [ ] **翻译状态可视化**：待翻译/翻译中/已完成/失败的微动画
- [ ] **进度条动效**：增加流畅的渐变动画
- [ ] **导航交互**：章节列表增加展开/收起、搜索过滤

### 4️⃣ 设置面板优化

#### 当前状态
- 6个引擎配置卡片网格排列
- 输入框+下拉框基础样式

#### 需优化项
- [ ] **引擎卡片设计**：为每个引擎设计独特的品牌标识
- [ ] **API Key安全展示**：输入时显示/隐藏切换，密钥脱敏显示
- [ ] **连接状态动画**：测试连接时的加载态、成功/失败反馈
- [ ] **配置分组**：按"云端API"和"本地部署"分组

### 5️⃣ 状态面板优化

#### 当前状态
- 统计数据卡片
- 环形进度条
- 引擎信息展示

#### 需优化项
- [ ] **数据可视化**：字符数、进度等用图表展示
- [ ] **扫描页高亮**：OCR页面特殊标记
- [ ] **时间线设计**：展示项目处理时间线

### 6️⃣ 交互动效优化

| 场景 | 当前状态 | 建议优化 |
|------|----------|----------|
| 标签切换 | 瞬间切换 | 添加slide/fade过渡 |
| 按钮点击 | 无反馈 | 添加press效果 |
| 卡片悬停 | 简单背景变化 | 添加scale/shadow变化 |
| 进度更新 | 逐段刷新 | 添加闪烁/高亮动画 |
| Toast通知 | 简单滑入 | 添加弹性动画 |

---

## 🎨 设计规范参考

### 配色方向建议

**方案A：科技蓝（推荐）**
```
--primary: #3B82F6 (更鲜亮的蓝)
--accent: #06B6D4 (青色点缀)
--bg-gradient: linear-gradient(135deg, #0F172A 0%, #1E293B 100%)
```

**方案B：金融绿**
```
--primary: #10B981 (祖母绿)
--accent: #F59E0B (琥珀色)
--bg-gradient: linear-gradient(135deg, #022c22 0%, #064E3B 100%)
```

**方案C：尊贵紫**
```
--primary: #8B5CF6 (紫)
--accent: #EC4899 (粉)
--bg-gradient: linear-gradient(135deg, #1E1B4B 0%, #312E81 100%)
```

### 字体建议

| 用途 | 推荐字体 | 字号 |
|------|----------|------|
| 标题 | Inter / Noto Sans SC | 24px / 20px |
| 正文 | Inter / Noto Sans SC | 14px |
| 代码/数字 | JetBrains Mono | 13px |
| 注释 | Inter | 12px |

### 间距系统

```css
:root {
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 24px;
    --space-6: 32px;
    --space-8: 48px;
}
```

---

## 🔌 前后端对接说明

### API接口（已就绪）

| 接口 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 服务健康检查 |
| `/api/upload` | POST | 文件上传解析 |
| `/api/translate` | POST | 翻译段落 |
| `/api/export/docx` | POST | 导出Word |
| `/api/downloads/{f}` | GET | 文件下载 |

### 前端调用示例

```javascript
// 翻译单段
const result = await fetch('/api/translate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        segments: [{index: 0, text: 'Hello'}],
        engine: 'deepseek',
        target_language: 'zh-Hans'
    })
});
```

### API服务地址
- 本地：`http://127.0.0.1:8000`
- Swagger文档：`http://127.0.0.1:8000/docs`

---

## 📱 响应式断点

```css
/* 移动端 */
@media (max-width: 640px) {
    .content-split { grid-template-columns: 1fr; }
    .sidebar { max-height: 150px; }
}

/* 平板 */
@media (max-width: 1024px) {
    .config-grid { grid-template-columns: 1fr; }
}

/* 桌面 */
@media (min-width: 1280px) {
    .content-split { grid-template-columns: 260px 1fr 1fr; }
}
```

---

## ⚠️ 注意事项

1. **不修改HTML结构**：当前DOM结构已与JS事件绑定，如需调整请与前端工程师确认
2. **保留CSS变量**：颜色/间距等使用CSS变量，便于后续主题切换
3. **图标规范**：推荐使用 [Lucide Icons](https://lucide.dev/) 或 [Heroicons](https://heroicons.com/)
4. **字体兼容性**：确保中英文混排显示正常，建议使用 [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC)

---

## ✅ 交付检查清单

完成优化后请确认：

- [ ] 所有页面视觉风格统一
- [ ] 动画流畅无卡顿
- [ ] 中文字体正确加载
- [ ] 移动端布局正常
- [ ] 无控制台报错
- [ ] 核心交互功能正常

---

**🎉 感谢配合！如有问题随时沟通。**

---
