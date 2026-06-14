<h1 align="center">🎯 智能广告投放系统</h1>
<h3 align="center">Open-Source Programmatic Advertising Platform</h3>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow" /></a>
  <a href="http://120.79.28.109"><img src="https://img.shields.io/badge/live_demo-🟢_online-brightgreen" /></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue" />
  <img src="https://img.shields.io/badge/react-18-61dafb" />
  <img src="https://img.shields.io/badge/concurrency-100K-ff69b4" />
</p>

---

> Real-time bidding, DeepFM-powered CTR prediction, live data bigscreen. Clone and run in 3 minutes.

🔗 **Live Demo:** [http://120.79.28.109](http://120.79.28.109) — `admin` / `admin123`

## ⚡ Quick Start

```bash
git clone https://github.com/torry991-coder/ad-placement-platform.git
cd ad-placement-platform

# Windows
start.bat

# macOS / Linux
chmod +x start.sh && ./start.sh
```

Opens at **http://localhost:5173** · Login: `admin` / `admin123`

---

## ✨ Features

| | |
|--|--|
| 🧠 **ML-powered Bidding** | DeepFM (PyTorch) → XGBoost → Statistical 3-tier CTR prediction. <5ms auction. |
| ⚡ **Real-Time Auctions** | 5 strategies: Max Conversions, Target CPA, Target ROAS, Enhanced CPC, Manual. |
| 📊 **Live Bigscreen** | Full-screen dark mode with Canvas particles and live auction waterfall. |
| 🔍 **RAG Knowledge Base** | 11 ad-tech expert docs. Ask "How to improve ROAS?" — zero-dependency TF-IDF search. |
| 📡 **WebSocket Streaming** | KPI updates, auction results, alerts pushed live to all dashboards. |
| 🧪 **A/B Experiments** | Bayesian + Frequentist. Auto-stop at significance. |
| 🎯 **Attribution** | 6 models: Last-touch through Shapley Data-driven. |
| 🔐 **RBAC** | admin / advertiser / analyst. JWT auth. |
| 📈 **Prometheus** | Standard `/api/metrics` endpoint. |
| ⌨️ **Command Palette** | `Ctrl+K` global search and navigation. |

---

## 🔧 Architecture

```
Browser ──→ React 18 + TypeScript (10 pages + Bigscreen)
                │
Nginx ──────────┼──── SSL + Load Balancer
                │
FastAPI ────────┼──── 50+ APIs, async SQLAlchemy 2.0
    ├── ML Engine   (DeepFM · XGBoost · Statistical)
    ├── RAG Service (11 docs · TF-IDF)
    ├── WebSocket   (Live streaming)
    ├── Agents      (6-agent AI pipeline)
    └── Middleware  (Rate limit · Metrics)
                │
Data ───────────┼──── SQLite / PostgreSQL + Redis + MinIO
                │
External ───────┼──── OpenAI · DeepSeek · Gemini · Ollama
```

> 📐 [Interactive SVG diagram →](docs/architecture.html)

---

## 🌐 线上部署

**[📋 阿里云完整部署指南 →](DEPLOY.md)**

```bash
# 买好阿里云服务器后，SSH 连上去，一行命令搞定：
curl -fsSL https://raw.githubusercontent.com/torry991-coder/ad-placement-platform/main/deploy.sh | bash
```

| 平台 | 费用 | 直达 |
|------|------|------|
| 阿里云轻量服务器 | **38元/年** | [立即购买](https://www.aliyun.com/daily-act/ecs/activity_selection) |
| GitHub Codespaces | 免费 | [![Open](https://img.shields.io/badge/Open_in_Codespaces-000?logo=github)](https://codespaces.new/torry991-coder/ad-placement-platform) |

---

## 📡 API

| Module | Key Endpoints |
|--------|--------------|
| Auth | `POST /api/auth/login` `POST /api/auth/register` |
| Campaigns | `GET/POST/PATCH/DELETE /api/campaigns/` |
| Bidding | `POST /api/bidding/auction` `GET /api/bidding/strategies` |
| Analytics | `GET /api/analytics/dashboard` `GET /api/analytics/trends` |
| RAG | `GET /api/rag/search?q=ROAS` |
| Reports | `GET /api/reports/export/{csv,pdf,xlsx}` |
| WebSocket | `ws://localhost:8000/ws/dashboard` |
| Events | `GET /api/event/track?type=impression` |
| Metrics | `GET /api/metrics` |

Full docs at `/api/docs` after startup.

---

## 🐳 Docker

```bash
docker compose up -d
```

---

## 📄 License

MIT
