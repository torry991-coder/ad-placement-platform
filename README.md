<h1 align="center">🎯 智能广告投放系统</h1>
<h3 align="center">Ad Placement Platform</h3>

<p align="center">
  <a href="http://120.79.28.109"><img src="https://img.shields.io/badge/demo-online-brightgreen" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow" /></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue" />
  <img src="https://img.shields.io/badge/react-18-61dafb" />
</p>

---

Open-source programmatic advertising platform with ML-powered bidding, real-time auctions, RAG knowledge base, and live data bigscreen.

🔗 **Demo:** http://120.79.28.109 · `admin` / `admin123`

## Quick Start

```bash
git clone https://github.com/torry991-coder/ad-placement-platform.git
cd ad-placement-platform

# Windows
start.bat

# macOS / Linux
chmod +x start.sh && ./start.sh
```

Opens at http://localhost:5173.

## Features

- 🧠 **ML Bidding** — DeepFM → XGBoost → Statistical 3-tier CTR prediction
- ⚡ **Real-Time Auctions** — 5 strategies: Max Conversions, Target CPA, Target ROAS, Enhanced CPC, Manual
- 📊 **Live Bigscreen** — Full-screen dark mode with Canvas particles and auction waterfall
- 🔍 **RAG Knowledge Base** — 11 ad-tech docs, TF-IDF search: "How to improve ROAS?"
- 🤖 **AI Agents** — 6-agent pipeline (Strategist, Copywriter, Budget, Auditor, Report, Audience)
- 🎛️ **User-Selectable LLM** — DeepSeek / OpenAI / Gemini / Ollama / Fallback
- 📡 **WebSocket Streaming** — Live KPI, auction results, alerts pushed to all dashboards
- 🧪 **A/B Experiments** — Bayesian + Frequentist, auto-stop at significance
- 🎯 **Attribution** — 6 models including Shapley Data-driven
- 🔐 **RBAC** — admin / advertiser / analyst, JWT auth
- ⌨️ **Command Palette** — `Ctrl+K` global search and navigation

## Architecture

```
Browser ──→ React 18 + TypeScript (10 pages + Bigscreen)
                │
FastAPI ────────┼──── 50+ APIs, async SQLAlchemy 2.0
    ├── ML Engine   (DeepFM · XGBoost · Statistical)
    ├── RAG Service (11 docs · TF-IDF)
    ├── WebSocket   (Live streaming)
    ├── Agents      (6-agent AI pipeline)
    └── Middleware  (Rate limit · Prometheus)
                │
Data ───────────┼──── SQLite / PostgreSQL
                │
External ───────┼──── DeepSeek · OpenAI · Gemini · Ollama
```

## API

| Module | Endpoints |
|--------|----------|
| Auth | `POST /api/auth/login` `POST /api/auth/register` |
| Campaigns | `GET/POST/PATCH/DELETE /api/campaigns/` |
| Bidding | `POST /api/bidding/auction` `GET /api/bidding/strategies` |
| Analytics | `GET /api/analytics/dashboard` `GET /api/analytics/trends` |
| LLM | `GET /api/llm/providers` `POST /api/llm/settings` |
| RAG | `GET /api/rag/search?q=ROAS` |
| WebSocket | `ws://localhost:8000/ws/dashboard` |
| Reports | `GET /api/reports/export/{csv,pdf,xlsx}` |
| Metrics | `GET /api/metrics` |

Full Swagger docs at `/api/docs`.

## Project Structure

```
ad-placement-platform/
├── backend/
│   ├── routes/          12 route modules
│   ├── services/        14 business engines
│   ├── models/          8 ORM tables
│   ├── llm/             LLM provider abstraction
│   └── agents/          6-agent AI pipeline
├── frontend/
│   └── src/
│       ├── pages/       10 pages + bigscreen
│       ├── components/  Dashboard, common, layout
│       └── services/    API client layer
├── docs/                Architecture diagrams
├── start.bat / start.sh One-click launchers
└── docker-compose.yml   Container deployment
```

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
