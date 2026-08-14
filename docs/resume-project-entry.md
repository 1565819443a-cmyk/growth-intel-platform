# 简历项目条目 · Growth Intelligence Platform

> 求职方向：金融数字化 / 风控数据架构 / 数据产品。中文版用于国内投递，英文版用于海外/国际化岗位。

---

## 中文版

### 增长智能分析平台 · Growth Intelligence Platform（个人项目 / 求职作品集）

**技术栈**：FastAPI · SQLAlchemy · React 19 + Vite + TypeScript · ECharts · PostgreSQL(Neon) · scikit-learn · scipy · lifetimes · DeepSeek LLM · Render/Vercel 部署

**在线演示**：https://growth-intel-platform.vercel.app ｜ 后端 API：https://growth-intel-api.onrender.com ｜ GitHub：github.com/1565819443a-cmyk/growth-intel-platform

**项目简介**：全栈构建跨境电商增长数据产品，从埋点原始日志（ODS）到数仓分层（DWD/DWS/ADS），完成用户分层与生命周期、营销组合模型（MMM）、裂变增长归因三大分析模块，并接入 LLM 流式生成经营策略报告，Neon + Render + Vercel 全线上部署。

**主要工作**：

- **自研模拟数仓（数据底座）**：固定随机种子生成 6 个月完整业务数据（15,000 用户 / 107 万事件 / 66,281 订单 / 16,062 邀请），构建 ODS→DWD→DWS→ADS 四层数仓，全链路可复现；SQLite（开发）与 PostgreSQL（生产）零改动切换。
- **用户分层与生命周期**：RFM 分层识别高价值客群（约 11.9% 用户贡献高价值）；BG-NBD + Gamma-Gamma 预测 90 天 LTV；GBM 流失预警模型 AUC 0.819，输出 Top 高风险流失名单与特征重要性。
- **营销组合模型 MMM**：几何 adstock（滞后衰减）+ Hill 饱和函数，scipy 最小二乘拟合各渠道贡献，输出渠道 ROAS / 边际 ROAS 与预算重分配建议（拉平边际回报，GMV 提升）。
- **裂变增长归因**：邀请关系树 → 月度 K 因子趋势（0.9→1.4，增长闭环）、激励阶梯 ROI（3/5/10 人档奖励成本 vs 带来的注册/首单/GMV）、裂变漏斗（浏览 16,968 → 分享 5,477 → 邀请注册 676 → 首单 492，每步自然衰减）。
- **数据可信度设计（本项目重点）**：通过「spend → 媒体拉动系数 → 订单数」注入渠道因果，让 MMM 能真实拟合而非硬编码；流失特征窗口截止观察期前 30 天严格防泄漏；三处邀请口径（被接受邀请数 == 邀请渠道注册 == invitee_id 回填）严格相等，保证分析结论可信、可复现、经得起追问。
- **AI 策略报告**：前端汇总三模块分析结果 → 后端组装 prompt → DeepSeek SSE 流式生成结构化报告（核心结论 + 分模块解读 + 可执行动作），无 key 时自动降级本地模板。
- **工程与部署**：GitHub 版本管理、Neon Postgres 生产库灌数、Render 后端（Blueprint 声明式配置 + 环境变量管理 + CORS 白名单）、Vercel 前端（Root Directory + 构建产物），全链路线上可用。

**收获亮点**：验证了「数据要讲得通」的工程方法——用因果注入 + 防泄漏 + 口径一致性把模拟数据做成可信的分析底座，而非拍脑袋造数；完整走通「数仓建模 → 统计分析 → 机器学习 → LLM 报告 → 线上部署」的数据产品闭环。

---

## English Version

### Growth Intelligence Platform (Solo Data Product · Portfolio Project)

**Stack**: FastAPI · SQLAlchemy · React 19 + Vite + TypeScript · ECharts · PostgreSQL (Neon) · scikit-learn · scipy · lifetimes · DeepSeek LLM · Render / Vercel

**Live demo**: https://growth-intel-platform.vercel.app ｜ API: https://growth-intel-api.onrender.com ｜ GitHub: github.com/1565819443a-cmyk/growth-intel-platform

**Overview**: Full-stack cross-border e-commerce growth analytics product. Built a simulated data warehouse (ODS → DWD → DWS → ADS) and three analytics modules — customer segmentation & lifecycle, Marketing Mix Modeling (MMM), and referral-growth attribution — then wired them into an LLM-generated executive strategy report. Deployed end-to-end on Neon / Render / Vercel.

**Highlights**:

- **Self-built simulated warehouse**: fixed-seed generator producing 6 months of consistent business data (15K users / 1.07M events / 66K orders / 16K invites); ODS→DWD→DWS→ADS four-layer warehouse, fully reproducible; transparent SQLite↔PostgreSQL switch.
- **Segmentation & lifecycle**: RFM tiers (≈11.9% high-value users); BG-NBD + Gamma-Gamma 90-day LTV forecast; GBM churn model with AUC 0.819 and a top-risk churn watchlist.
- **MMM**: geometric adstock + Hill saturation fitted via scipy least-squares → per-channel contribution, ROAS / marginal ROAS, and budget re-allocation recommendations (leveling marginal returns to lift GMV).
- **Referral attribution**: invite-graph → monthly viral coefficient K-factor trend (0.9 → 1.4); incentive-tier ROI; referral funnel (16,968 browsed → 5,477 shared → 676 signed up → 492 first purchase).
- **Data credibility as a feature**: injected spend→media-multiplier→orders causality so MMM genuinely fits; strict 30-day feature-window to avoid label leakage; invite metrics equal across three independent definitions — the numbers hold up to scrutiny.
- **LLM report**: frontend aggregates module outputs → DeepSeek streams a structured strategy report (insights + module walk-through + actionable next steps), with local-template fallback.
- **Engineering & deployment**: Git workflow, Neon Postgres seeding, Render backend (declarative Blueprint + env management + CORS allowlist), Vercel frontend (root directory + build output) — fully live in production.
