"""总览：核心 KPI 卡片 + 每日趋势 + 渠道 ROI 概览。"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .queries import load_kpi_daily, load_users, load_channel_daily, load_user_daily


def overview(session) -> Dict[str, Any]:
    kpi = load_kpi_daily(session)
    if kpi.empty:
        return {"error": "无 KPI 数据"}
    users = load_users(session)
    ch = load_channel_daily(session)
    ud = load_user_daily(session)

    total_gmv = float(kpi["gmv"].sum())
    total_orders = int(kpi["orders"].sum())
    total_spend = float(kpi["total_spend"].sum())

    # MAU：最近 30 天活跃去重用户
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    mau = int(ud[ud["stat_date"] >= cutoff]["user_id"].nunique())

    # 渠道汇总（花费 / GMV / ROAS）
    ch_agg = ch.groupby("channel").agg(
        spend=("spend", "sum"), gmv=("gmv", "sum")
    ).reset_index()
    ch_agg = ch_agg.sort_values("gmv", ascending=False)
    channels = [
        {
            "channel": r.channel,
            "spend": round(float(r.spend), 1),
            "gmv": round(float(r.gmv), 1),
            "roas": round(float(r.gmv / r.spend), 3) if r.spend else 0.0,
        }
        for r in ch_agg.itertuples()
    ]

    trend = [
        {
            "date": r.stat_date.strftime("%Y-%m-%d"),
            "gmv": round(float(r.gmv), 1),
            "orders": int(r.orders),
            "new_users": int(r.new_users),
            "active_users": int(r.active_users),
            "roas": round(float(r.roas), 3),
        }
        for r in kpi.itertuples()
    ]

    return {
        "period": {
            "start": kpi["stat_date"].min().strftime("%Y-%m-%d"),
            "end": kpi["stat_date"].max().strftime("%Y-%m-%d"),
        },
        "summary": {
            "total_gmv": round(total_gmv, 1),
            "total_orders": total_orders,
            "total_users": int(len(users)),
            "mau": mau,
            "aov": round(total_gmv / total_orders, 2) if total_orders else 0.0,
            "total_spend": round(total_spend, 1),
            "roas": round(total_gmv / total_spend, 3) if total_spend else 0.0,
        },
        "channels": channels,
        "trend": trend,
    }
