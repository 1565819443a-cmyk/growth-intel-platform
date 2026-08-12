"""裂变增长归因：邀请关系 / K 因子 / 激励阶梯 ROI / 裂变漏斗。

- K 因子：每月人均有效邀请（被接受的邀请数 / 当月活跃分享者数）
- 阶梯 ROI：3/5/10 人档位 → 每档奖励成本 vs 带来的首单 / GMV
- 漏斗：浏览邀请页 → 分享链接 → 邀请注册 → 首单（ads_growth_funnel）
- 邀请关系：Top 邀请人的邀请规模与下游 GMV
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .queries import load_invites, load_users, load_orders, load_kpi_daily


def _month_key(d) -> str:
    return pd.to_datetime(d).strftime("%Y-%m")


def growth_summary(session) -> Dict[str, Any]:
    invites = load_invites(session)
    users = load_users(session)
    orders = load_orders(session)
    kpi = load_kpi_daily(session)

    if invites.empty:
        return {"error": "无邀请数据"}

    invites["invite_date"] = pd.to_datetime(invites["invite_date"])
    invites["month"] = invites["invite_date"].apply(_month_key)

    # ---------- K 因子（按月） ----------
    # 有效邀请数：accepted 的邀请；分享者数：当月发过邀请的独立用户
    sent = invites.groupby("month").agg(
        inviters=("inviter_id", "nunique"),
        invites_sent=("invite_id", "size"),
        accepted=("accepted", "sum"),
    ).reset_index()
    sent["k_factor"] = sent["accepted"] / sent["inviters"].clip(lower=1)

    k_factor = [
        {"month": r.month, "k_factor": round(float(r.k_factor), 3),
         "inviters": int(r.inviters), "invites_sent": int(r.invites_sent),
         "accepted": int(r.accepted)}
        for r in sent.itertuples()
    ]

    # ---------- 激励阶梯 ROI ----------
    tiers = invites.groupby("reward_tier").agg(
        invites_sent=("invite_id", "size"),
        accepted=("accepted", "sum"),
        reward_cost=("reward_amount", "sum"),
    ).reset_index().sort_values("reward_tier")

    # 被邀请用户：从 dim_user 里 register_channel='invite'，关联 inviter
    inv_users = users[users["register_channel"] == "invite"].copy()
    inv_users["inviter_id"] = pd.to_numeric(inv_users["inviter_id"], errors="coerce")
    # 每个被邀请用户的激励档位 = 其对应接受邀请的 reward_tier（invitee_id 精确回链）
    accepted_inv = invites[invites["accepted"] == 1]
    tier_by_invitee = accepted_inv[accepted_inv["invitee_id"].notna()].set_index("invitee_id")["reward_tier"]
    inv_users["tier"] = inv_users["user_id"].map(tier_by_invitee).fillna(0).astype(int)

    # 被邀请用户首单与累计 GMV
    ord_agg = orders.groupby("user_id").agg(
        first_order=("order_date", "min"),
        gmv=("amount", "sum"),
        orders_n=("order_id", "size"),
    ).reset_index()
    inv_users = inv_users.merge(ord_agg, on="user_id", how="left")
    inv_users["gmv"] = inv_users["gmv"].fillna(0.0)
    inv_users["orders_n"] = inv_users["orders_n"].fillna(0)
    inv_users["has_first_order"] = inv_users["first_order"].notna()

    tier_roi = []
    for r in tiers.itertuples():
        sub = inv_users[inv_users["tier"] == r.reward_tier]
        tier_roi.append({
            "tier": int(r.reward_tier),                     # 档位（达到 N 人）
            "invites_sent": int(r.invites_sent),
            "accepted": int(r.accepted),
            "reward_cost": round(float(r.reward_cost), 1),
            "registered": int(len(sub)),
            "first_order": int(sub["has_first_order"].sum()),
            "gmv": round(float(sub["gmv"].sum()), 1),
            "roi": round(float(sub["gmv"].sum() / r.reward_cost), 3) if r.reward_cost else 0.0,
        })

    # ---------- 漏斗（最近 30 天平均转换率） ----------
    funnel = _funnel_rate(session)

    # ---------- Top 邀请人 ----------
    # 被邀请用户 → 邀请人映射
    inv_to_inviter = inv_users[["user_id", "inviter_id"]].set_index("user_id")["inviter_id"]
    inviter_stats = invites.groupby("inviter_id").agg(
        invites_sent=("invite_id", "size"),
        accepted=("accepted", "sum"),
    ).reset_index()
    inviter_stats["registered"] = inviter_stats["inviter_id"].map(
        inv_to_inviter.value_counts()
    ).fillna(0)
    # 下游 GMV = 该邀请人带来的邀请用户 GMV 之和
    inv_gmv = inv_users.set_index("user_id")["gmv"]
    downstream = pd.DataFrame({
        "inviter_id": inv_to_inviter.values,
        "gmv": inv_gmv.reindex(inv_to_inviter.index).values,
    }).groupby("inviter_id")["gmv"].sum()
    inviter_stats["downstream_gmv"] = inviter_stats["inviter_id"].map(downstream).fillna(0.0)

    top_inviters = inviter_stats.sort_values("accepted", ascending=False).head(20)
    top_list = [
        {
            "inviter_id": int(r.inviter_id),
            "invites_sent": int(r.invites_sent),
            "accepted": int(r.accepted),
            "registered": int(r.registered),
            "downstream_gmv": round(float(r.downstream_gmv), 1),
        }
        for r in top_inviters.itertuples()
    ]

    return {
        "total_invites": int(len(invites)),
        "total_accepted": int(invites["accepted"].sum()),
        "k_factor_trend": k_factor,
        "latest_k_factor": round(float(sent["k_factor"].iloc[-1]), 3) if len(sent) else 0.0,
        "tier_roi": tier_roi,
        "funnel": funnel,
        "top_inviters": top_list,
    }


def _funnel_rate(session) -> Dict[str, Any]:
    """裂变漏斗最近 30 天汇总 + 各环节转化率（跨 SQLite/Postgres 通用）。

    观察窗口以表内最大日期为基准（而非系统当前时间），保证部署后与数据范围一致。
    """
    import pandas as pd
    from sqlalchemy import text

    last = session.execute(text(
        "SELECT MAX(funnel_date) FROM ads_growth_funnel"
    )).scalar()
    if not last:
        return {"steps": [], "conversion": []}
    cutoff = (pd.Timestamp(last) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    df = pd.read_sql(text(
        "SELECT funnel_date, step, users FROM ads_growth_funnel "
        "WHERE funnel_date >= :cutoff ORDER BY funnel_date"
    ), session.bind, params={"cutoff": cutoff})
    if df.empty:
        return {"steps": [], "conversion": []}
    df["funnel_date"] = pd.to_datetime(df["funnel_date"])
    g = df.groupby("step")["users"].sum()
    order = ["浏览邀请页", "分享链接", "邀请注册", "首单"]
    steps = [{"step": s, "users": int(g.get(s, 0))} for s in order if g.get(s, 0) > 0]
    conv = []
    for i in range(1, len(steps)):
        prev = steps[i - 1]["users"]
        conv.append({
            "from": steps[i - 1]["step"],
            "to": steps[i]["step"],
            "rate": round(steps[i]["users"] / prev, 4) if prev else 0.0,
        })
    return {"steps": steps, "conversion": conv}


def invite_tree(session, inviter_id: int | None = None) -> Dict[str, Any]:
    """邀请关系网络（前 N 条关系，用于前端图谱）。"""
    invites = load_invites(session)
    users = load_users(session)
    accepted = invites[invites["accepted"] == 1].copy()
    if inviter_id is not None:
        accepted = accepted[accepted["inviter_id"] == inviter_id]
    accepted = accepted.head(300)

    name_map = users.set_index("user_id")
    links = []
    for r in accepted.itertuples():
        links.append({
            "source": int(r.inviter_id),
            "target": int(r.invitee_id) if pd.notna(r.invitee_id) else None,
            "tier": int(r.reward_tier),
            "reward": float(r.reward_amount),
        })
    links = [l for l in links if l["target"] is not None]
    return {"links": links, "count": len(links)}
