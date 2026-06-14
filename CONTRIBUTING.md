# Contributing

感谢你的贡献！请遵循以下指南。

## 开发环境

```bash
# 克隆
gh repo clone <your>/ad-placement-platform
cd ad-placement-platform

# 后端
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install
```

## 代码规范

- **Python**: Black 格式化, 88字符行宽
- **TypeScript**: Prettier 格式化, 2空格缩进
- **提交信息**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

## 提交流程

1. Fork & clone
2. 创建分支: `git checkout -b feat/your-feature`
3. 开发 + 测试
4. `git commit -m "feat: 你的功能描述"`
5. Push & 发起 PR

## 项目结构

```
backend/
├── main.py          FastAPI entry
├── routes/          API endpoints (10 modules)
├── services/        Business engines (11 modules)
├── models/          SQLAlchemy ORM
├── middleware/      Rate limit, metrics, etc.
└── schemas/         Pydantic models

frontend/
└── src/
    ├── pages/       9 pages + bigscreen
    ├── components/  Reusable components
    ├── hooks/       Custom React hooks
    └── services/    API client layer
```

## Issue 报告

使用 Bug Report / Feature Request 模板，提供：
- 环境信息 (OS, Python/Node 版本)
- 复现步骤
- 期望 vs 实际行为
