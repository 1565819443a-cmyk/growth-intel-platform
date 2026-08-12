# Growth Intelligence Platform · 增长智能分析平台

跨境电商增长数据产品：一套模拟数据底座 + 三个增长分析模块 + LLM 生成经营策略报告。

数据工程师视角的全栈实现 —— 从埋点原始日志（ODS）到数仓分层（DWD/DWS/ADS），到 RFM 分层、BG-NBD 生命周期预测、流失预警模型、营销组合模型（MMM）与裂变增长归因，最后接入 DeepSeek 流式生成可执行策略报告。

**在线演示：** 前端 `https://xxx.vercel.app` · 后端 API `https://xxx.onrender.com`（部署后填入）

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · SQLAlchemy · pandas / numpy / scipy / scikit-learn / lifetimes |
| 数据 | 模拟数仓：ODS → DWD → DWS → ADS 四层，SQLite（本地）/ PostgreSQL · Neon（生产） |
| 建模 | RFM 分层 · BG-NBD + Gamma-Gamma LTV · GBM 流失预警 · adstock+Hill 饱和 MMM · K 因子归因 |
| LLM | DeepSeek Chat（OpenAI 兼容），SSE 流式生成策略报告 |
| 前端 | React 19 · Vite · TypeScript · ECharts · Tailwind |
| 部署 | Render（后端）· Vercel（前端）· Neon（Postgres） |

---

## 三个分析模块

**1. 用户分层与生命周期**（`/users`）
- RFM 分层：高价值 / 高潜力 / 流失预警 / 沉睡 / 新客，分群规模 + 人均 GMV
- 队列 LTV：按注册周观察累计收入曲线，BG-NBD + Gamma-Gamma 预测未来 90 天 LTV
- 流失预警：梯度提升分类器，输出 Top 高风险名单 + 特征重要性（AUC 0.82）

**2. 营销组合模型 MMM**（`/mmm`）
- 几何 adstock（滞后衰减）+ Hill 饱和函数，scipy 最小二乘拟合渠道贡献
- 各渠道贡献占比、ROAS、边际 ROAS；预算重分配建议（拉平边际回报，GMV 提升 %）

**3. 裂变增长归因**（`/growth`）
- 邀请关系 → 每月 K 因子趋势（0.9 → 1.4，增长故事）
- 激励阶梯 ROI（3/5/10 人档奖励成本 vs 带来注册/首单/GMV）
- 裂变漏斗：浏览邀请页 → 分享 → 邀请注册 → 首单

**AI 经营策略报告**（`/report`）
前端汇总以上分析 → POST `/api/report` → DeepSeek 流式生成结构化的「结论 + 分模块解读 + 可执行动作」，逐字渲染。

---

## 数据可信度设计（本项目的重点）

用固定随机种子生成 6 个月（2026-02-01 ~ 2026-07-31）完整业务数据，全链路可复现（`seed_data.py` 重灌即得同样结果）：

- **数据量级**：15,000 用户 · 1,077,067 事件 · 66,281 订单 · 16,062 邀请
- **邀请链路一致**：注册 2850 名邀请渠道用户 == 被接受邀请数 2850 == invitee_id 精确回填，三处口径严格相等
- **流失标签不泄漏**：churn 特征窗口截止观察期前 30 天，标签按真实沉默定义，AUC 0.819（非作弊也不失真）
- **渠道因果注入**：spend → 媒体拉动系数 → 订单数，让 MMM 能「拟合」出各渠道贡献
- **漏斗单调**：56666 → 18115 → 2850 → 1988，每步自然衰减

---

## 本地运行

```bash
# 1. 后端
cd backend
python3.9 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 填入 DEEPSEEK_API_KEY（可留空，报告页降级为本地模板）
python scripts/seed_data.py   # 生成模拟数据 + 建数仓四层 + 入库（约 1-2 分钟）
uvicorn app.main:app --port 8000

# 2. 前端（另开终端）
cd frontend
npm install
npm run dev                   # http://localhost:5173，/api 自动代理到 8000
```

---

## 生产部署（Neon + Render + Vercel）

### 1. Neon：Postgres 数据库
1. [neon.tech](https://neon.tech) 注册 → New Project（选离你最近的 region）→ 复制连接串（Pooled 或 Direct 均可）
2. `DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/growth_intel?sslmode=require`

### 2. 灌入种子数据（本地跑，把数据写进 Neon）
```bash
cd backend
DATABASE_URL="postgresql://user:pass@ep-xxx.../growth_intel?sslmode=require" \
  .venv/bin/python scripts/seed_data.py
```

### 3. Render：后端 API
- 推代码到 GitHub → Render 面板 **New → Blueprint** → 选仓库（自动读取 `deploy/render.yaml`）
- 填入 3 个 secret 环境变量：
  - `DATABASE_URL` = Neon 连接串
  - `DEEPSEEK_API_KEY` = DeepSeek key
  - `FRONTEND_ORIGIN` = Vercel 前端地址（如 `https://growth-intel.vercel.app`）
- 部署后验证：`curl https://<service>.onrender.com/api/health` → `{"status":"ok"}`

### 4. Vercel：前端
- Vercel **Add New → Project** → 导入同一仓库，Root Directory 选 `frontend`
- 配置环境变量：`VITE_API_BASE = https://<service>.onrender.com`
- 部署后打开前端，全链路验证：总览 → 三模块 → AI 报告

> 免费层冷启动约 30s ~ 1min，首次打开略慢属正常。

---

## 目录结构

```
growth-intel-platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS
│   │   ├── config.py            # 环境变量
│   │   ├── db.py                # SQLAlchemy（SQLite/Postgres 自动切换）
│   │   ├── models.py            # ORM 四层表定义
│   │   ├── routers/             # overview / users / mmm / growth / report
│   │   └── services/
│   │       ├── data_gen.py      # 模拟数据生成器（固定种子，全可复现）
│   │       ├── warehouse.py     # ODS→DWD→DWS→ADS 数仓构建
│   │       ├── rfm.py / ltv.py / churn.py / mmm.py / growth_attribution.py
│   │       └── report_gen.py    # DeepSeek 报告（prompt + SSE 流式，无 key 降级模板）
│   ├── scripts/seed_data.py     # 灌数入口
│   └── requirements.txt
├── frontend/                    # React 19 + Vite + ECharts
│   └── src/
│       ├── api/client.ts        # 统一 API（VITE_API_BASE 可切换后端）
│       └── pages/               # Overview / Users / Mmm / Growth / Report
└── deploy/                      # render.yaml / vercel.json
```

## 简历一句话

> 全栈构建跨境电商「增长智能分析平台」：自研模拟数仓（ODS→DWD→DWS→ADS，15k 用户 / 107 万事件，固定种子全可复现），实现 RFM 分层、BG-NBD 生命周期预测、GBM 流失预警（AUC 0.82）、adstock+Hill 饱和 MMM 预算分配、邀请裂变 K 因子归因，并接入 DeepSeek 流式生成经营策略报告；后端 FastAPI + 前端 React + LLM，Neon/Render/Vercel 全线上部署。
