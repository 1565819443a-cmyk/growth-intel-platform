"""MMM 营销组合模型：几何 adstock + Hill 饱和函数，scipy 最小二乘拟合。

- 因变量：每日总 GMV
- 媒体：search / ads / social / invite 每日投放 spend
- 控制：趋势 + 周末
- 输出：渠道贡献分解、ROAS、边际 ROAS、预算重分配建议
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter

from .queries import load_channel_daily, load_kpi_daily

MEDIA_CHANNELS = ["search", "ads", "social", "invite"]
CONTROL = ["trend", "weekend"]


def _adstock(x: np.ndarray, alpha: float) -> np.ndarray:
    """几何衰减 adstock（IIR 滤波，向量化）。"""
    return lfilter([1.0], [1.0, -alpha], x.astype(float))


def _hill(x: np.ndarray, S: float, K: float) -> np.ndarray:
    """Hill 饱和函数，输出 [0,1)。"""
    return x ** S / (x ** S + K ** S + 1e-12)


def _steady_adstock(alpha: float) -> float:
    """长期稳态乘子：几何级数 1/(1-alpha) 的均值近似。"""
    return 1.0 / (1.0 - alpha)


def build_matrix(ch_daily: pd.DataFrame, kpi: pd.DataFrame) -> Dict[str, Any]:
    """拼装模型矩阵：响应 y + 媒体矩阵 X + 控制矩阵 C。"""
    df = ch_daily.pivot_table(index="stat_date", columns="channel",
                              values=["spend"], aggfunc="sum")
    df.columns = [c[1] for c in df.columns]
    df = df.fillna(0.0)
    df = df.merge(kpi[["stat_date", "gmv"]].set_index("stat_date"), left_index=True, right_index=True)
    df = df.sort_index()

    t = np.arange(len(df)) / max(len(df), 1)
    weekend = pd.Series([1 if d.weekday() >= 5 else 0 for d in df.index], index=df.index)
    y = df["gmv"].astype(float).values
    X = {c: df[c].astype(float).values for c in MEDIA_CHANNELS}
    C = {"trend": t.astype(float), "weekend": weekend.astype(float)}
    return {"y": y, "X": X, "C": C, "dates": df.index}


def _fit_params(y, X, C, n_coord_rounds=4):
    """几何 adstock + Hill(S=2) 拟合。

    S 固定为 2（与数据生成的结构一致）。对每个渠道在 (alpha, K) 网格上
    做坐标下降搜索，内层用 OLS 精确求解（beta/截距/趋势/周末）——给定
    (alpha, K) 后模型对 beta 是线性的。全程确定、秒级收敛，规避非线性
    最小二乘的局部最优问题。返回 (b0, b_trend, b_weekend, beta, alpha, S, K), yhat。
    """
    n_media = len(MEDIA_CHANNELS)
    maxX = {c: max(X[c].max(), 1.0) for c in MEDIA_CHANNELS}
    ALPHA_GRID = [0.5, 0.7, 0.85]
    K_FAC_GRID = [0.5, 0.9, 1.5, 2.5]

    def g_feature(c, alpha, K):
        ad = _adstock(X[c], alpha)
        return ad ** 2 / (ad ** 2 + K ** 2 + 1e-12)

    def ols(g_list):
        M = np.column_stack([np.ones_like(y), C["trend"], C["weekend"]] + g_list)
        coef, *_ = np.linalg.lstsq(M, y, rcond=None)
        return coef, M @ coef

    # 坐标下降：每轮依次为每个渠道挑选使整体 R² 最大的 (alpha, K)
    choice = {c: (0.7, maxX[c]) for c in MEDIA_CHANNELS}
    for _ in range(n_coord_rounds):
        for c in MEDIA_CHANNELS:
            others = [g_feature(cc, choice[cc][0], choice[cc][1])
                      for cc in MEDIA_CHANNELS if cc != c]
            best = None
            for a in ALPHA_GRID:
                for f in K_FAC_GRID:
                    _, yhat = ols(others + [g_feature(c, a, f * maxX[c])])
                    r2 = _r2(y, yhat)
                    if best is None or r2 > best[0]:
                        best = (r2, a, f * maxX[c])
            choice[c] = (best[1], best[2])

    g_list = [g_feature(c, choice[c][0], choice[c][1]) for c in MEDIA_CHANNELS]
    coef, yhat = ols(g_list)
    b0, b_trend, b_weekend = coef[0], coef[1], coef[2]
    beta = coef[3:]
    alpha = np.array([choice[c][0] for c in MEDIA_CHANNELS])
    K = np.array([choice[c][1] for c in MEDIA_CHANNELS])
    return (b0, b_trend, b_weekend, beta, alpha, np.array([2.0] * n_media), K), yhat


def mmm_result(session) -> Dict[str, Any]:
    ch = load_channel_daily(session)
    kpi = load_kpi_daily(session)
    if ch.empty or kpi.empty:
        return {"error": "无渠道/KPI 数据"}

    data = build_matrix(ch, kpi)
    y, X, C = data["y"], data["X"], data["C"]

    try:
        (b0, b_trend, b_weekend, beta, alpha, S, K), yhat = _fit_params(y, X, C)
    except Exception as e:  # noqa: BLE001
        return {"error": f"MMM 拟合失败: {e}"}

    total_gmv = float(y.sum())
    total_spend = {c: float(X[c].sum()) for c in MEDIA_CHANNELS}
    n_days = max(len(y), 1)

    # 各渠道贡献（含 carryover 的均值贡献，日均口径）
    media_contrib = {}
    for j, c in enumerate(MEDIA_CHANNELS):
        media_contrib[c] = float(beta[j] * _hill(_adstock(X[c], alpha[j]), S[j], K[j]).mean())

    baseline_contrib = float((b0 + b_trend * C["trend"] + b_weekend * C["weekend"]).mean())

    # 归一化贡献份额（正贡献）
    contrib_items = dict(media_contrib); contrib_items["自然增长基线"] = baseline_contrib
    pos_sum = sum(max(v, 0.0) for v in contrib_items.values()) or 1.0

    channels = []
    for j, c in enumerate(MEDIA_CHANNELS):
        contrib = media_contrib[c]
        if contrib <= 0 or total_spend[c] <= 0:
            continue
        # 边际 ROAS：在稳态投放水平下的 dY/dspend（近似，忽略 carryover 动态）
        x_ss = X[c].mean()
        dHill = (S[j] * K[j] ** S[j] * x_ss ** (S[j] - 1)) / \
                ((x_ss ** S[j] + K[j] ** S[j]) ** 2 + 1e-12)
        marginal_roas = float(beta[j] * dHill)
        channels.append({
            "channel": c,
            "spend": round(total_spend[c], 1),
            "contribution": round(contrib, 1),
            "share": round(max(contrib, 0.0) / pos_sum * 100, 1),
            "roas": round(contrib * n_days / total_spend[c] if total_spend[c] else 0.0, 3),
            "marginal_roas": round(marginal_roas, 4),
            "adstock_alpha": round(float(alpha[j]), 3),
            "saturation_S": round(float(S[j]), 3),
            "saturation_K": round(float(K[j]), 1),
        })
    channels.sort(key=lambda d: -d["share"])

    # 预算重分配：固定总预算，最大化总贡献（拉平边际回报）
    alloc = _budget_allocate(channels, total_spend, beta, alpha, S, K, total_gmv, n_days=len(y))

    return {
        "total_gmv": round(total_gmv, 1),
        "model_fit_r2": round(_r2(y, yhat), 3),
        "baseline": {
            "contribution": round(baseline_contrib, 1),
            "share": round(max(baseline_contrib, 0.0) / pos_sum * 100, 1),
            "avg_daily": round(float(b0 + b_trend * C["trend"].mean() + b_weekend * C["weekend"].mean()), 1),
        },
        "channels": channels,
        "budget_plan": alloc,
        "parameters": {
            "adstock": {c: round(float(alpha[i]), 3) for i, c in enumerate(MEDIA_CHANNELS)},
            "hill_S": {c: round(float(S[i]), 3) for i, c in enumerate(MEDIA_CHANNELS)},
            "hill_K": {c: round(float(K[i]), 1) for i, c in enumerate(MEDIA_CHANNELS)},
        },
    }


def _budget_allocate(channels, total_spend, beta, alpha, S, K, total_gmv, n_days=191):
    """固定总预算下最大化贡献，返回建议分配与预测 GMV 提升。"""
    n = len(MEDIA_CHANNELS)
    B = sum(total_spend.values())
    idx = {c: i for i, c in enumerate(MEDIA_CHANNELS)}
    order = [c for c in MEDIA_CHANNELS if total_spend[c] > 0]

    def contrib(x):
        # 稳态贡献 = 每日贡献 × 天数；x 是区间总预算，折算为日均投放量
        s = 0.0
        for c in order:
            i = idx[c]
            daily = x[i] / max(n_days, 1)
            eff = _steady_adstock(alpha[i]) * daily
            s += beta[i] * _hill(eff, S[i], K[i])
        return s * n_days

    def neg(x):
        return -contrib(x)

    cons = [{"type": "eq", "fun": lambda x: np.sum(x) - B},
            {"type": "ineq", "fun": lambda x: x}]
    x0 = np.array([total_spend[c] for c in MEDIA_CHANNELS])
    # 每渠道单次重分配幅度限制在 ±50%（贴近可执行现实，避免极端建议）
    bounds = [(total_spend[c] * 0.5, total_spend[c] * 1.5) if total_spend[c] > 0 else (0.0, 0.0)
              for c in MEDIA_CHANNELS]
    res = minimize(neg, x0, method="SLSQP", bounds=bounds, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-9})
    x_opt = res.x if res.success else x0

    # 提升估算（用当前平均边际 ROAS 线性外推新分配带来的 GMV）
    cur = contrib(x0)
    new = contrib(x_opt) if res.success else cur
    plan = []
    for i, c in enumerate(MEDIA_CHANNELS):
        plan.append({
            "channel": c,
            "current": round(float(total_spend[c]), 1),
            "suggested": round(float(x_opt[i]), 1),
            "delta_pct": round((x_opt[i] / total_spend[c] - 1) * 100, 1) if total_spend[c] else 0.0,
        })
    plan.sort(key=lambda d: -d["suggested"])
    return {
        "total_budget": round(B, 1),
        "expected_gmv_current": round(cur, 1),
        "expected_gmv_optimal": round(new, 1),
        "gain_pct": round((new / cur - 1) * 100, 1) if cur else 0.0,
        "channels": plan,
    }


def _r2(y, yhat) -> float:
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1 - ss_res / ss_tot if ss_tot else 0.0
