# 智能广告投放系统 - 企业级升级方案 & Google 对标分析

> 目标：将项目从「课程作业级别」提升到「企业级商用产品」，与 Google Ads Smart Bidding / Performance Max 进行全面对标。

---

## 一、Google Ads 企业级能力全景

Google Ads 目前处理 **每天 85 亿+ 搜索**，每次拍卖处理 **7000万+ 信号**，核心架构如下：

| 能力维度 | Google Ads 当前水平 | 我们的初始方案 | 差距 |
|---------|-------------------|-------------|------|
| **出价策略** | 7种策略(Max Conv/CPA/ROAS/CPC/CPM等) | 仅 XGBoost + Bandit | ❌ 单一 |
| **信号处理** | 70M实时信号/拍卖 | 离线批量预测 | ❌ 非实时 |
| **创意优化** | AI自动生成+测试多种素材组合 | 仅重写文案 | ❌ 缺视觉 |
| **A/B实验** | 内置实验框架，自动显著性检验 | 无 | ❌ 缺失 |
| **受众定向** | 自定义受众+信号引导+Lookalike | 无 | ❌ 缺失 |
| **多渠道** | Search/Display/YouTube/Gmail/Maps/Shopping | 单平台模拟 | ❌ 单渠道 |
| **预算节奏** | Budget pacing, 日预算平滑 | 无 | ❌ 缺失 |
| **学习期** | 2-6周自动适应，新冷启动 | 无 | ❌ 缺失 |
| **报告系统** | 频道级报告+归因模型+洞察 | 基础图表 | ❌ 基础 |
| **安全合规** | 品牌安全+负面词+政策审查 | 仅文案审查Agent | ⚠️ 部分 |
| **API集成** | Google Ads API + Meta API | 仅模拟数据 | ❌ 全模拟 |
| **告警规则** | 自动化异常告警+规则引擎 | 无 | ❌ 缺失 |

---

## 二、升级后的企业级架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端 (React + TypeScript + Tailwind)            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Campaign │ │ Dashboard│ │ Creative │ │ A/B Experiments    │  │
│  │ Manager  │ │ + Charts │ │ Studio   │ │ + Statistical Tests│  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │ Audience │ │ Budget   │ │ Alerts & │ │ Settings + API Key │  │
│  │ Segments │ │ Pacing   │ │ Rules    │ │ Config             │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP/SSE/WebSocket
┌───────────────────────────────┴──────────────────────────────────┐
│                      后端 (FastAPI + Celery)                       │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 广告活动   │  │ 实时出价 │  │ 预算     │  │ A/B实验引擎  │  │
│  │ CRUD +     │  │ 引擎     │  │ 分配引擎 │  │ (统计检验)   │  │
│  │ 排期       │  │ (ms级)   │  │ + Pacing │  │              │  │
│  └────────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 受众定向   │  │ 创意优化 │  │ 规则引擎 │  │ 归因模型     │  │
│  │ + 信号     │  │ + 疲劳   │  │ + 告警   │  │ (Last-touch, │  │
│  │            │  │ 检测     │  │          │  │  Multi-touch) │  │
│  └────────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               LLM 多Agent 智能管道                         │   │
│  │  审计Agent → 策略Agent → 创意Agent → 受众Agent            │   │
│  │  + 预算Agent + 报告Agent                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               ML 引擎层                                    │   │
│  │  XGBoost(CTR/CVR预测) + DeepFM + Thompson/UCB + RL(DQN)   │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌───────────────────────────────┴──────────────────────────────────┐
│               数据层 (PostgreSQL/SQLite + Redis + MinIO)           │
│  campaigns │ ads │ ad_groups │ audiences │ creatives │ experiments│
│  performance_metrics │ budgets │ alerts │ attribution_logs      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 三、功能对比矩阵：升级后 vs Google Ads

| 功能模块 | 升级后我们的系统 | Google Ads | 对标程度 |
|---------|----------------|-----------|---------|
| **多出价策略** | MaxConv / tCPA / tROAS / Manual | 7种全有 | ✅ 80% |
| **实时竞价** | Redis缓存 + 微秒级预测API | 70M信号/拍卖 | ⚠️ 模拟层 |
| **CTR/CVR预测** | XGBoost + DeepFM双模型 | 自有深度模型 | ✅ 接近 |
| **强化学习出价** | DQN + Thompson Sampling | 大规模RL | ✅ 路径一致 |
| **A/B实验** | 贝叶斯+频率派双检验 | 内置实验框架 | ✅ 完整 |
| **创意优化** | LLM文案+疲劳检测+自动轮换 | 自动优化+素材组合 | ✅ 80% |
| **受众定向** | 自定义受众+相似扩展+信号引导 | Audience Signals | ✅ 对标 |
| **多渠道** | 模拟Google/Meta/TikTok/Twitter | 全Google生态 | ⚠️ 模拟 |
| **预算管理** | Budget Pacing + 跨渠道分配 | 共享预算+Pacing | ✅ 完整 |
| **归因模型** | Last-touch/Linear/Time-decay/Data-driven | 多种归因 | ✅ 完整 |
| **报告系统** | Dashboard + PDF/CSV导出+对比 | 频道级报告 | ✅ 90% |
| **告警规则** | 自定义阈值+自动触发+通知 | 自动化规则 | ✅ 完整 |
| **合规审查** | LLM自动政策审查 | 自动+人工 | ✅ 对标 |
| **API集成** | 预留 Ad Platform Connectors | 原生API | ⚠️ 模拟 |
| **冷启动** | 渐进式学习期+探索策略 | 2-6周学习期 | ✅ 对齐 |
| **深色模式** | 支持 | 支持 | ✅ |

**总结：升级后覆盖 Google Ads 约 75-80% 的功能面，核心算法路径一致，差距主要在真实广告网络集成和信号规模。**

---

## 四、升级项目目录结构

```
智能广告投放系统/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # 数据库连接 (PostgreSQL/SQLite)
│   ├── models/
│   │   ├── campaign.py            # 广告活动
│   │   ├── ad_group.py            # 广告组
│   │   ├── creative.py            # 创意素材
│   │   ├── audience.py            # 受众定向
│   │   ├── budget.py              # 预算 & Pacing
│   │   ├── experiment.py          # A/B实验
│   │   └── alert.py               # 告警规则
│   ├── services/
│   │   ├── bidding_engine.py      # 实时竞价引擎
│   │   ├── ml_engine.py           # CTR/CVR预测 (XGBoost + DeepFM)
│   │   ├── budget_pacer.py        # 预算节奏控制
│   │   ├── ab_testing.py          # A/B实验+统计检验
│   │   ├── attribution.py         # 归因模型
│   │   ├── audience_service.py    # 受众分析+扩展
│   │   ├── creative_rotator.py    # 创意轮换+疲劳检测
│   │   ├── rule_engine.py         # 规则引擎+自动告警
│   │   ├── report_generator.py    # 报告生成 (PDF/CSV)
│   │   └── ad_platforms/          # 广告平台连接器 (预留)
│   │       ├── base.py
│   │       ├── google_ads.py
│   │       └── meta_ads.py
│   ├── agents/
│   │   ├── auditor.py             # 审计Agent
│   │   ├── strategist.py          # 策略Agent
│   │   ├── copywriter.py          # 创意Agent
│   │   ├── audience_agent.py      # 受众Agent
│   │   ├── budget_agent.py        # 预算Agent
│   │   ├── report_agent.py        # 报告Agent
│   │   └── pipeline.py            # Agent编排+SSE流
│   ├── routes/
│   │   ├── campaigns.py
│   │   ├── bidding.py
│   │   ├── analytics.py
│   │   ├── experiments.py
│   │   ├── audiences.py
│   │   ├── alerts.py
│   │   └── reports.py
│   ├── llm/
│   │   ├── service.py             # 多Provider LLM服务
│   │   └── providers.py           # OpenAI/Gemini/Ollama适配
│   ├── tasks/
│   │   └── scheduler.py           # 定时任务(预算重置/报告)
│   ├── requirements.txt
│   └── sample_data.csv
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Navbar.tsx
│   │   │   │   └── DashboardLayout.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── KPICards.tsx          # 实时KPI
│   │   │   │   ├── TrendChart.tsx        # 趋势折线图
│   │   │   │   ├── ChannelPie.tsx        # 渠道饼图
│   │   │   │   ├── AdRankBar.tsx         # 广告排行
│   │   │   │   ├── BudgetGauge.tsx       # 预算仪表盘
│   │   │   │   └── Heatmap.tsx           # 时段热力图
│   │   │   ├── campaigns/
│   │   │   │   ├── CampaignForm.tsx      # 创建向导
│   │   │   │   ├── CampaignList.tsx      # 列表+搜索+过滤
│   │   │   │   ├── CampaignDetail.tsx    # 详情页
│   │   │   │   └── BudgetSlider.tsx      # 可视化预算调整
│   │   │   ├── creative/
│   │   │   │   ├── CreativeStudio.tsx    # 创意管理
│   │   │   │   ├── AdPreview.tsx         # 多格式预览
│   │   │   │   └── FatigueMeter.tsx      # 疲劳度检测
│   │   │   ├── experiments/
│   │   │   │   ├── ExperimentCreate.tsx  # 创建A/B测试
│   │   │   │   ├── ExperimentResults.tsx # 统计显著性
│   │   │   │   └── VariantComparison.tsx # 变体对比
│   │   │   ├── audience/
│   │   │   │   ├── AudienceBuilder.tsx   # 受众构建器
│   │   │   │   └── SegmentInsights.tsx   # 受众洞察
│   │   │   ├── ai/
│   │   │   │   ├── AgentPanel.tsx        # AI助手面板
│   │   │   │   ├── AgentStream.tsx       # SSE流式输出
│   │   │   │   └── Recommendation.tsx    # 智能建议卡片
│   │   │   ├── alerts/
│   │   │   │   ├── AlertConfig.tsx
│   │   │   │   └── AlertHistory.tsx
│   │   │   └── common/
│   │   │       ├── DataTable.tsx         # 通用表格(排序/搜索/分页)
│   │   │       ├── FilterBar.tsx
│   │   │       ├── DateRangePicker.tsx
│   │   │       ├── StatCard.tsx
│   │   │       └── LoadingStates.tsx
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── CampaignsPage.tsx
│   │   │   ├── CreativePage.tsx
│   │   │   ├── ExperimentsPage.tsx
│   │   │   ├── AudiencePage.tsx
│   │   │   ├── ReportsPage.tsx
│   │   │   ├── AlertsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── services/
│   │   │   ├── api.ts                  # Axios封装
│   │   │   ├── campaigns.ts
│   │   │   ├── bidding.ts
│   │   │   ├── agent.ts                # SSE连接
│   │   │   └── types.ts                # TypeScript类型
│   │   ├── hooks/
│   │   │   ├── useSSE.ts
│   │   │   ├── useDebounce.ts
│   │   │   └── useLocalStorage.ts
│   │   ├── store/
│   │   │   └── campaignStore.ts        # Zustand状态管理
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css                   # Tailwind入口
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── package.json
├── .env.example
├── docker-compose.yml                  # PostgreSQL + Redis + MinIO
└── README.md
```

---

## 五、详细功能说明

### 5.1 实时竞价引擎
- 内存缓存热门广告的CTR预测值
- 多策略支持: Max Conversions, Target CPA, Target ROAS, Enhanced CPC, Manual
- 每次请求处理时间 < 10ms (本地模拟环境)
- 模拟真实拍卖: 多广告主竞争 + 质量分 + Ad Rank

### 5.2 A/B实验完整框架
- 创建实验: 选择对照组/实验组，设定流量分配比例
- 统计检验: 贝叶斯后验概率 + 频率派 t-test + 置信区间计算
- 可视化: 概率密度图 + 累计收益曲线 + 胜出概率
- 自动停止: 达到统计显著性时自动结束实验

### 5.3 预算节奏控制 (Budget Pacing)
- 日预算平滑: 防止预算过早耗尽
- 时段分桶: 按小时分配预算权重
- 超支保护: 达到阈值自动暂停
- 跨渠道再分配: 高ROAS渠道自动获得更多预算

### 5.4 归因模型
- Last-touch / First-touch / Linear / Time-decay / Position-based
- Data-driven: 基于Shapley值的算法归因
- 可视化: 转化路径桑基图

### 5.5 受众分析
- 自定义受众分组 (年龄/设备/地域/时段/兴趣)
- 受众级ROAS对比
- 相似受众扩展 (基于高价值用户特征)
- 实时信号反馈

### 5.6 规则引擎与告警
- 自定义阈值: CPC > X, CTR < Y, 预算消耗 > Z%
- 自动动作: 暂停/降预算/发通知
- 通知渠道: UI内 + Email + Webhook

### 5.7 创意管理与疲劳检测
- 多素材管理 + 预览(搜索/展示/视频格式)
- 疲劳度指标: 展示次数/CTR衰减
- 自动轮换: 疲劳素材自动退场，新素材上线
- LLM辅助: 根据表现数据建议新文案方向

### 5.8 6-Agent智能管道
- **审计Agent**: 全账户健康检查
- **策略Agent**: 出价+预算建议
- **创意Agent**: 文案重写+素材建议
- **受众Agent**: 受众扩展建议
- **预算Agent**: Pacing调整建议
- **报告Agent**: 自动生成周报/月报

---

## 六、前端交互能力 (企业级)

| 交互特征 | 实现方式 |
|---------|---------|
| 实时数据更新 | WebSocket / SSE 推送 KPI变化 |
| 拖拽式预算调整 | Slider + 实时预估 |
| 内联编辑 | 表格内直接编辑出价/预算/状态 |
| 向导式创建 | Step-by-step 广告活动创建向导 |
| 搜索+过滤+排序 | DataTable通用组件 |
| 数据导出 | CSV/PDF一键导出 |
| 深色/浅色模式 | Tailwind Dark Mode |
| 响应式设计 | 桌面+平板+手机适配 |
| 骨架屏/Loading | 全部异步状态处理 |
| Toast通知 | 操作成功/失败/告警通知 |
| 无限滚动 | 大数据列表自动分页加载 |
| 快捷键支持 | 常用操作键盘快捷键 |

---

## 七、数据库设计 (8张核心表)

1. **campaigns** - 广告活动 (名称/预算/策略/状态/排期)
2. **ad_groups** - 广告组 (定向/出价/所属活动)
3. **creatives** - 创意素材 (文案/图片URL/类型/表现数据)
4. **audience_segments** - 受众分组 (规则/成员数/标签)
5. **budget_logs** - 预算消耗日志 (按小时)
6. **experiments** - A/B实验 (配置/结果/状态)
7. **alert_rules** - 告警规则 (条件/动作/状态)
8. **performance_metrics** - 效果数据 (展示/点击/转化/花费/CPC/CTR/ROAS)

---

## 八、实施计划 (26个任务, 6个阶段)

### Phase 1: 基础架构 & 数据库 (4 tasks)
- Task 1: 项目初始化 + 配置文件 + Docker
- Task 2: 数据库模型全部8张表 + 迁移
- Task 3: FastAPI骨架 + 路由注册 + 中间件
- Task 4: React + Tailwind + Vite骨架 + 路由

### Phase 2: 广告活动管理 (4 tasks)  
- Task 5: Campaign CRUD API + AdGroup CRUD
- Task 6: Campaign前端管理界面(列表/创建/详情)
- Task 7: 创意管理 + 疲劳检测
- Task 8: CSV导入 + 模拟数据生成器

### Phase 3: 竞价与分析引擎 (5 tasks)
- Task 9: CTR/CVR预测模型 (XGBoost + DeepFM)
- Task 10: 实时竞价引擎 (多策略)
- Task 11: 预算节奏控制
- Task 12: 受众分析 + 扩展服务
- Task 13: 归因模型 (5种算法)

### Phase 4: A/B实验 & 规则 (3 tasks)
- Task 14: A/B实验引擎 + 统计检验
- Task 15: 规则引擎 + 告警
- Task 16: 报告生成器 (PDF/CSV)

### Phase 5: LLM Agent & 前端 (6 tasks)
- Task 17: LLM多Provider服务
- Task 18: 6-Agent管道实现 + SSE流式
- Task 19: 仪表盘首页 (KPI+图表+实时)
- Task 20: A/B实验前端
- Task 21: 受众+告警前端
- Task 22: AI助手面板(对话+建议)

### Phase 6: 打磨 (4 tasks)
- Task 23: 深色模式 + 响应式 + 动效
- Task 24: 性能优化 + 错误处理 + Loading states
- Task 25: 文档 + README + API文档
- Task 26: Docker一键部署

---

## 九、技术依赖

### 后端 (Python)
```
fastapi, uvicorn, sqlalchemy, alembic, pydantic
xgboost, scikit-learn, numpy, pandas
deepctr-torch (DeepFM), torch
redis, celery
jinja2 (PDF报告), openpyxl (CSV)
openai, google-generativeai, ollama (LLM)
```

### 前端 (TypeScript)
```
react, react-router-dom, zustand
tailwindcss, recharts, lucide-react
axios, date-fns, react-hot-toast
@tanstack/react-table, framer-motion
```

### 基础设施
```
PostgreSQL (推荐) 或 SQLite (简易模式)
Redis (实时竞价缓存) 
MinIO (创意素材存储)
Docker Compose
```
