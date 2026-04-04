# 更新日志

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-04

### Added
- 全新 PDF 翻译工作台界面
- 多引擎支持：DeepSeek, OpenAI, DeepL, Claude, Ollama, 千问, MiniMax
- 四种导出模式：段落交替、左右分栏、纯译文、脚注模式
- 翻译缓存功能，避免重复翻译
- 智能 PDF 解析，支持文本、表格、公式提取
- 进度显示和预估时间
- 暂停/继续功能

### Changed
- 重构代码结构，采用模块化设计
- 优化翻译并发性能
- 改进前端界面用户体验

### Fixed
- 修复导出文件名中文编码问题
- 修复翻译循环中的异常处理
- 修复启动弹窗问题（静默启动模式）

## [0.1.0] - 2024-12-01

### Added
- 初始版本
- 基本 PDF 翻译功能
- 单引擎支持（DeepSeek）

---

历史版本记录详见 [GitHub Releases](https://github.com/your-username/taixuan-translator/releases)