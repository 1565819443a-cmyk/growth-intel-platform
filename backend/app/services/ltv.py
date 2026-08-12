"""LTV 分析：注册队列留存/累计收入曲线 + BG-NBD / Gamma-Gamma 预测。

- 队列曲线：按注册周分群，展示每群在注册后各周的用户留存率与人均累计 GMV。
- 预测模型：lifetimes 库，BG-NBD 预测未来 90 天购买次数 × Gamma-Gamma
  预测单次交易金额 → predicted_ltv，写回 ads_user_seg.predicted_ltv。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter

from .queries import load_user_daily, load_users, load_orders


def _cohort_key(d) -> str:
    """注册周 key：ISO 周一日期。"""
    return (d - pd.Timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def cohort_curves(session, horizon_weeks: int = 8) -> Dict[str, Any]:
    """注册队列 → 留存率 & 人均累计 LTV 曲线。"""
    daily = load_user_daily(session)
    users = load_users(session)
    orders = load_orders(session)
    end = pd.Timestamp(users["register_date"].max()) if len(users) else pd.Timestamp.now()

    # 队列（按注册周）
    users["cohort"] = users["register_date"].apply(_cohort_key)
    cohort_order = sorted(users["cohort"].unique())
    cohort_size = users.groupby("cohort")["user_id"].count()

    # 活跃日归属队列：以 user 注册周为准
    daily = daily.merge(users[["user_id", "cohort"]], on="user_id", how="left")
    daily["cohort_ts"] = pd.to_datetime(daily["cohort"])
    daily["week_offset"] = (
        daily["stat_date"].sub(daily["cohort_ts"]).dt.days // 7
    ).astype(int)

    # 留存率：第 w 周仍活跃用户数 / 队列人数
    retention = daily[daily["week_offset"].between(0, horizon_weeks - 1)] \
        .groupby(["cohort", "week_offset"])["user_id"].nunique().reset_index()
    retention = retention.merge(cohort_size.rename("cohort_size"), on="cohort", how="left")
    retention["rate"] = retention["user_id"] / retention["cohort_size"]

    # 人均累计 GMV：按周累计订单
    orders["cohort"] = orders["user_id"].map(users.set_index("user_id")["cohort"])
    orders["week_offset"] = orders["order_date"].sub(
        orders["cohort"].apply(lambda c: pd.Timestamp(c))
    ).dt.days // 7
    orders = orders[orders["week_offset"].between(0, horizon_weeks - 1)]
    rev = orders.groupby(["cohort", "week_offset"])["amount"].sum().reset_index()
    rev["cum_gmv_per_user"] = rev.groupby("cohort")["amount"].cumsum() / rev["cohort"].map(cohort_size)

    # 只保留样本足够多的队列（注册人数 >= 100），最多展示 8 个
    kept = [c for c in cohort_order if cohort_size.get(c, 0) >= 100][-8:]

    retention_curves = []
    for c in kept:
        r = retention[retention["cohort"] == c].set_index("week_offset")["rate"]
        retention_curves.append({
            "cohort": c,
            "size": int(cohort_size[c]),
            "rates": [round(float(r.get(w, 0.0)), 3) for w in range(horizon_weeks)],
        })

    ltv_curves = []
    for c in kept:
        r = rev[rev["cohort"] == c].set_index("week_offset")["cum_gmv_per_user"]
        ltv_curves.append({
            "cohort": c,
            "size": int(cohort_size[c]),
            "values": [round(float(r.get(w, 0.0)), 1) for w in range(horizon_weeks)],
        })

    return {
        "horizon_weeks": horizon_weeks,
        "weeks": list(range(horizon_weeks)),
        "retention": retention_curves,
        "ltv": ltv_curves,
    }


def predict_ltv(session, horizon_days: int = 90, writeback: bool = False) -> Dict[str, Any]:
    """BG-NBD + Gamma-Gamma 预测未来 horizon_days 的 LTV。

    观察期：首次购买 ~ 最新订单日（以全量数据截止为准）。
    """
    orders = load_orders(session)
    if orders.empty:
        return {"error": "无订单数据"}

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    end = orders["order_date"].max()

    g = orders.groupby("user_id").agg(
        first=("order_date", "min"),
        last=("order_date", "max"),
        n=("order_date", "count"),
    )
    g["total"] = orders.groupby("user_id")["amount"].sum()
    g.columns = ["first", "last", "n", "total"]
    # T 与 recency 以天为单位
    T = (end - g["first"]).dt.days.astype(float).clip(lower=1)
    recency = (g["last"] - g["first"]).dt.days.astype(float).clip(lower=0)
    frequency = (g["n"] - 1).clip(lower=0)
    monetary = g["total"] / g["n"]  # 平均客单价（含首单，Gamma-Gamma 通常用复购；此处近似）

    df = pd.DataFrame({"frequency": frequency, "recency": recency, "T": T,
                       "monetary_value": monetary}).reset_index()
    df.columns = ["user_id", "frequency", "recency", "T", "monetary_value"]

    # 训练样本：frequency >= 1 有完整交易史
    bgf = BetaGeoFitter(penalizer_coef=0.01)
    sample = df[df["frequency"] >= 1]
    bgf.fit(sample["frequency"], sample["recency"], sample["T"])

    # 期望未来交易次数
    t = horizon_days
    df["expected_purchases"] = bgf.conditional_expected_number_of_purchases_up_to_time(
        t, df["frequency"], df["recency"], df["T"]
    )

    # Gamma-Gamma：仅用有复购的用户拟合客单价
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(df.loc[df["frequency"] >= 1, "frequency"],
            df.loc[df["frequency"] >= 1, "monetary_value"])
    df["expected_monetary"] = ggf.conditional_expected_average_profit(
        df["frequency"], df["monetary_value"]
    ).clip(lower=0)

    df["predicted_ltv"] = (df["expected_purchases"] * df["expected_monetary"]).clip(lower=0)

    if writeback:
        from sqlalchemy import text
        session.execute(
            text("UPDATE ads_user_seg SET predicted_ltv = :v WHERE user_id = :u"),
            [{"v": float(v), "u": int(u)} for v, u in zip(df["predicted_ltv"], df["user_id"])],
        )
        session.commit()

    # 输出：分布 + 抽样 top 预测
    df["ltv_bucket"] = pd.cut(
        df["predicted_ltv"],
        bins=[0, 50, 100, 200, 400, 800, np.inf],
        labels=["<50", "50-100", "100-200", "200-400", "400-800", ">800"],
    )
    dist = (df["ltv_bucket"].value_counts().sort_index()
            .rename("count").reset_index())
    buckets = [
        {"bucket": str(r.ltv_bucket), "count": int(r.count)}
        for r in dist.itertuples()
    ]

    return {
        "horizon_days": horizon_days,
        "observation_end": str(end.date()),
        "model_users": int(len(df)),
        "avg_predicted_ltv": round(float(df["predicted_ltv"].mean()), 1),
        "median_predicted_ltv": round(float(df["predicted_ltv"].median()), 1),
        "distribution": buckets,
    }
