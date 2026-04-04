# 贡献指南

感谢您对太玄智译项目的关注！欢迎提交 Issue 和 Pull Request。

## 如何贡献

### 报告问题
1. 搜索现有 Issue 是否已存在
2. 创建新 Issue，描述：
   - 问题描述
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息

### 提交代码
1. Fork 本仓库
2. 创建功能分支：git checkout -b feature/your-feature
3. 进行开发并提交
4. 推送分支：git push origin feature/your-feature
5. 创建 Pull Request

### 代码规范
- 遵循 PEP 8
- 使用 type hints
- 编写单元测试
- 更新文档

### 提交信息格式
`
type(scope): 简短描述

详细描述（可选）

Fixes #issue-number
`

类型（type）：
- feat: 新功能
- fix: Bug 修复
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 维护

## 开发环境设置

`ash
# 克隆项目
git clone https://github.com/your-username/taixuan-translator.git
cd taixuan-translator

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy

# 运行测试
pytest

# 代码格式化
black .
flake8 .
`

## 联系方式

- 邮箱：taixuan@studio.example.com
- Issue：https://github.com/your-username/taixuan-translator/issues