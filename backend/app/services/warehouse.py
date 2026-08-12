"""数仓分层构建：ODS → DWD → DWS → ADS。

seed_data.py 调用：生成模拟数据 → 写入 ODS → 清洗明细 → DWD → 聚合 DWS → 应用层 ADS。
"""
from __future__ import annotations

from datetime import time, datetime

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from . import data_gen
from ..config import settings
from ..models import (
    RawUser, RawEvent, RawOrder, RawChannelSpend, RawInvite,
    DwdEventFact, DwdOrderFact, DwdInviteFact, DimUser,
    DwsUserDaily, DwsChannelDaily, DwsInviteDaily,
    AdsKpiDaily, AdsUserSeg, AdsChannelRoi, AdsGrowthFunnel,
)


def _clean(df: pd.DataFrame):
    """NaN → None，保证 SQLAlchemy 可插入。

    注意：float64 列直接 .where(..., None) 会把 None 还原成 NaN，必须先转 object。
    """
    df = df.copy()
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_object_dtype(s):
            continue
        if s.isna().any():
            df[col] = s.astype(object).where(s.notna(), None)
    return df


def _executemany(engine: Engine, table, df: pd.DataFrame, chunk: int = 50000):
    if df.empty:
        return
    rows = _clean(df).to_dict(orient="records")
    with engine.begin() as conn:
        for i in range(0, len(rows), chunk):
            conn.execute(table.insert(), rows[i:i + chunk])


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def build_warehouse(engine: Engine) -> dict:
    start = datetime.strptime(settings.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(settings.end_date, "%Y-%m-%d").date()
    n_users = settings.n_users

    print(f"[1/6] 生成模拟数据 {settings.n_users} 用户, {start} ~ {end} ...")
    users, invites = data_gen.gen_users(start, end, n_users)
    # 先算渠道投放 → 得到每日媒体拉动系数 + 直接归因订单 → 再生成订单（注入 spend→GMV 因果）
    channel_spend = data_gen.gen_channel_spend(start, end)
    lift_map = data_gen.get_media_lift(channel_spend)
    attribution = data_gen.get_media_attribution(channel_spend)
    events, orders = data_gen.gen_events_and_orders(users, end, lift_map=lift_map, attribution=attribution)
    print(f"     users={len(users)} events={len(events)} orders={len(orders)} invites={len(invites)}")

    # ---------------- ODS ----------------
    print("[2/6] 写入 ODS 原始表 ...")
    _executemany(engine, RawUser.__table__, users[[
        "user_id", "register_channel", "register_time", "register_date",
        "city", "device", "inviter_id",
    ]])
    _executemany(engine, RawInvite.__table__, pd.DataFrame({
        "invite_id": np.arange(1, len(invites) + 1),
        "inviter_id": invites["inviter_id"].astype(int),
        "invitee_id": None,  # 只有被接受的邀请才有注册用户
        "invite_time": invites["invite_time"],
        "invite_date": invites["invite_time"].dt.date,
        "reward_tier": invites["tier"],
        "reward_amount": invites["reward"],
        "accepted": invites["accepted"],
    }))
    # 回填被接受邀请的 invitee_id（= 邀请渠道用户）。
    # 用 data_gen 生成的 via_invite_id 精确映射（invitee 是通过该 invite_id 被邀请的），
    # 避免旧实现的「时间相近贪心匹配」在重编号后错配邀请链路。
    invitee_map = users.dropna(subset=["via_invite_id"]) \
        .set_index("via_invite_id")["user_id"].astype(int).to_dict()
    with engine.begin() as conn:
        for inv_id, uid in invitee_map.items():
            conn.execute(text("UPDATE raw_invites SET invitee_id=:u WHERE invite_id=:i"),
                         {"u": int(uid), "i": int(inv_id)})

    _executemany(engine, RawEvent.__table__, pd.DataFrame({
        "event_id": events["event_id"],
        "user_id": events["user_id"],
        "event_name": events["event_name"],
        "event_time": [datetime.combine(d, time(12, 0)) for d in events["event_date"]],
        "event_date": events["event_date"],
        "item_id": events["item_id"],
        "amount": events["amount"],
        "category": events["category"],
        "order_channel": events["order_channel"],
    }))
    _executemany(engine, RawOrder.__table__, pd.DataFrame({
        "order_id": orders["order_id"],
        "user_id": orders["user_id"],
        "order_date": orders["order_date"],
        "order_time": [datetime.combine(d, time(12, 0)) for d in orders["order_date"]],
        "amount": orders["amount"],
        "category": orders["category"],
        "order_channel": orders["order_channel"],
        "is_first_order": orders["is_first_order"],
    }))
    _executemany(engine, RawChannelSpend.__table__, channel_spend)

    # ---------------- DWD ----------------
    print("[3/6] 构建 DWD 明细 ...")
    _executemany(engine, DwdEventFact.__table__, pd.DataFrame({
        "event_id": events["event_id"],
        "user_id": events["user_id"],
        "event_name": events["event_name"],
        "event_date": events["event_date"],
        "event_time": [datetime.combine(d, time(12, 0)) for d in events["event_date"]],
        "item_id": events["item_id"],
        "amount": events["amount"],
        "category": events["category"],
        "order_channel": events["order_channel"],
    }))
    _executemany(engine, DwdOrderFact.__table__, pd.DataFrame({
        "order_id": orders["order_id"],
        "user_id": orders["user_id"],
        "order_date": orders["order_date"],
        "order_time": [datetime.combine(d, time(12, 0)) for d in orders["order_date"]],
        "amount": orders["amount"],
        "category": orders["category"],
        "order_channel": orders["order_channel"],
        "is_first_order": orders["is_first_order"],
    }))
    # DWD 邀请事实：用生成的 invites + 从 raw_invites 回读的 invitee_id
    with engine.begin() as conn:
        iid_map = dict(conn.execute(text(
            "SELECT invite_id, invitee_id FROM raw_invites"
        )).fetchall())
    dwd_inv = pd.DataFrame({
        "invite_id": np.arange(1, len(invites) + 1),
        "inviter_id": invites["inviter_id"].astype(int),
        "invitee_id": [iid_map.get(i) for i in np.arange(1, len(invites) + 1)],
        "invite_date": invites["invite_time"].dt.date,
        "invite_time": invites["invite_time"],
        "reward_tier": invites["tier"],
        "reward_amount": invites["reward"],
        "accepted": invites["accepted"],
    })
    _executemany(engine, DwdInviteFact.__table__, dwd_inv)
    _executemany(engine, DimUser.__table__, pd.DataFrame({
        "user_id": users["user_id"],
        "register_channel": users["register_channel"],
        "register_date": users["register_date"],
        "city": users["city"],
        "device": users["device"],
        "inviter_id": users["inviter_id"],
        "invite_source": np.where(users["inviter_id"].notna(), "invited", "organic"),
    }))

    # ---------------- DWS ----------------
    print("[4/6] 构建 DWS 主题宽表 ...")
    # 用户每日：事件聚合
    ev = events.copy()
    ev_g = ev.groupby(["user_id", "event_date"])["event_name"].value_counts().unstack(fill_value=0).reset_index()
    for col in ["app_open", "view_item", "add_to_cart", "purchase", "invite_click", "invite_share"]:
        if col not in ev_g.columns:
            ev_g[col] = 0
    od_g = orders.groupby(["user_id", "order_date"])["amount"].agg(["count", "sum"]).reset_index()
    od_g.columns = ["user_id", "stat_date", "orders", "gmv"]

    user_daily = ev_g.rename(columns={"event_date": "stat_date"}).merge(
        od_g, on=["user_id", "stat_date"], how="left"
    )
    user_daily["orders"] = user_daily["orders"].fillna(0)
    user_daily["gmv"] = user_daily["gmv"].fillna(0.0)
    dim = users[["user_id", "register_channel", "register_date"]]
    user_daily = user_daily.merge(dim, on="user_id", how="left")
    user_daily["is_new"] = user_daily["stat_date"] == user_daily["register_date"]
    user_daily["is_active"] = user_daily["app_open"] > 0
    user_daily = user_daily.rename(columns={
        "app_open": "app_opens", "view_item": "views", "add_to_cart": "add_to_cart",
    })
    user_daily = user_daily[[
        "stat_date", "user_id", "register_channel", "register_date", "is_new", "is_active",
        "app_opens", "views", "add_to_cart", "orders", "gmv", "invite_click", "invite_share",
    ]].rename(columns={"invite_click": "invite_clicks", "invite_share": "invite_shares"})
    user_daily = user_daily.sort_values(["stat_date", "user_id"])
    _executemany(engine, DwsUserDaily.__table__, user_daily)

    # 渠道每日
    ch_g = user_daily.groupby(["register_channel", "stat_date"]).agg(
        new_users=("is_new", "sum"),
        orders=("orders", "sum"),
        gmv=("gmv", "sum"),
    ).reset_index()
    ch_daily = ch_g.merge(
        channel_spend.rename(columns={"spend_date": "stat_date", "channel": "register_channel"}),
        on=["register_channel", "stat_date"], how="left",
    )
    ch_daily["spend"] = ch_daily["spend"].fillna(0.0)
    ch_daily["impressions"] = ch_daily["impressions"].fillna(0).astype(int)
    ch_daily["clicks"] = ch_daily["clicks"].fillna(0).astype(int)
    ch_daily = ch_daily.rename(columns={"register_channel": "channel"})
    _executemany(engine, DwsChannelDaily.__table__, ch_daily)

    # 邀请每日
    inv_g = invites.groupby(invites["invite_time"].dt.date).agg(
        invites_sent=("accepted", "size"),
        invites_accepted=("accepted", "sum"),
        reward_amount=("reward", lambda s: s[invites["accepted"]].sum()),
    ).reset_index().rename(columns={"index": "stat_date"})
    inv_g.columns = ["stat_date", "invites_sent", "invites_accepted", "reward_amount"]
    inv_new = users[users["register_channel"] == "invite"].copy()
    inv_new["invite_date"] = inv_new["register_date"]
    inv_new_users = inv_new.groupby("invite_date").size().reset_index(name="new_users") \
                           .rename(columns={"invite_date": "stat_date"})
    inv_new_gmv = inv_new.merge(
        orders.groupby("user_id")["amount"].sum().reset_index(), on="user_id", how="left"
    ).groupby("invite_date")["amount"].sum().reset_index(name="new_user_gmv")
    inv_daily = inv_g.merge(inv_new_users, on="stat_date", how="left") \
                     .merge(inv_new_gmv.rename(columns={"invite_date": "stat_date"}), on="stat_date", how="left")
    inv_daily["new_users"] = inv_daily["new_users"].fillna(0).astype(int)
    inv_daily["new_user_gmv"] = inv_daily["new_user_gmv"].fillna(0.0)
    _executemany(engine, DwsInviteDaily.__table__, inv_daily)

    # ---------------- ADS ----------------
    print("[5/6] 构建 ADS 应用层 ...")
    kpi = user_daily.groupby("stat_date").agg(
        gmv=("gmv", "sum"),
        orders=("orders", "sum"),
        new_users=("is_new", "sum"),
        active_users=("is_active", "sum"),
        paid_users=("orders", lambda s: (s > 0).sum()),
    ).reset_index()
    spend_by_day = ch_daily.groupby("stat_date")["spend"].sum()
    kpi["total_spend"] = kpi["stat_date"].map(spend_by_day).fillna(0.0)
    kpi["conversion_rate"] = np.where(kpi["active_users"] > 0, kpi["paid_users"] / kpi["active_users"], 0.0)
    kpi["roas"] = np.where(kpi["total_spend"] > 0, kpi["gmv"] / kpi["total_spend"], 0.0)
    kpi["invite_accept_rate"] = kpi["stat_date"].map(
        inv_daily.set_index("stat_date")["invites_accepted"] / inv_daily.set_index("stat_date")["invites_sent"]
    ).fillna(0.0)
    _executemany(engine, AdsKpiDaily.__table__, kpi)

    # 用户分层（基础 RFM 规则；LTV 预测 / 流失概率由服务模块更新）
    seg = _build_user_seg(users, orders, events, end)
    _executemany(engine, AdsUserSeg.__table__, seg)

    roi = ch_daily.groupby("channel").agg(
        spend=("spend", "sum"), gmv=("gmv", "sum")
    ).reset_index()
    roi["roas"] = np.where(roi["spend"] > 0, roi["gmv"] / roi["spend"], 0.0)
    roi["stat_date"] = end
    roi["attributed_share"] = 0.0
    _executemany(engine, AdsChannelRoi.__table__, roi)

    funnel = _build_funnel(events, users, orders, end)
    _executemany(engine, AdsGrowthFunnel.__table__, funnel)

    print("[6/6] 数仓构建完成")
    return {"users": len(users), "events": len(events), "orders": len(orders),
            "invites": len(invites), "days": (end - start).days + 1}


# --------------------------------------------------------------------------
# ADS 辅助
# --------------------------------------------------------------------------
def _build_user_seg(users: pd.DataFrame, orders: pd.DataFrame, events: pd.DataFrame, end) -> pd.DataFrame:
    seg = users[["user_id"]].copy()
    seg["register_date"] = users["register_date"]

    last_active = events.groupby("user_id")["event_date"].max()
    seg["last_active"] = seg["user_id"].map(last_active).fillna(seg["register_date"])
    seg["recency_days"] = [(end - d).days for d in seg["last_active"]]

    freq = orders.groupby("user_id")["order_id"].count()
    mon = orders.groupby("user_id")["amount"].sum()
    seg["frequency"] = seg["user_id"].map(freq).fillna(0).astype(int)
    seg["monetary"] = seg["user_id"].map(mon).fillna(0.0)
    seg["lifetime_value"] = seg["monetary"]

    days_reg = [(end - d).days for d in seg["register_date"]]
    # 高价值阈值：top 15% 消费额（p85）+ 至少 3 次购买 + 近期活跃，
    # 让高价值占比落在 ~13%（8-18% 目标中段），避免「高价值用户过多」的失真。
    m_p85 = seg["monetary"].quantile(0.85)
    m_p50 = seg["monetary"].quantile(0.50)
    # RFM 分层规则（低优先级先赋，高优先级后赋覆盖，保证互斥）：
    #   沉睡 → 流失预警 → 高潜力 → 高价值 → 新客(最后覆盖)
    seg["rfm_class"] = "一般"
    seg.loc[(seg["recency_days"] > 30) & (seg["monetary"] == 0), "rfm_class"] = "沉睡"
    # 流失预警 = 曾消费但已沉默 30 天以上（需要挽回的高风险用户）
    seg.loc[(seg["recency_days"] > 30) & (seg["monetary"] > 0), "rfm_class"] = "流失预警"
    seg.loc[(seg["monetary"] >= m_p50) & (seg["frequency"] >= 1) & (seg["recency_days"] <= 30), "rfm_class"] = "高潜力"
    seg.loc[(seg["monetary"] >= m_p85) & (seg["frequency"] >= 3) & (seg["recency_days"] <= 30), "rfm_class"] = "高价值"
    seg.loc[[d <= 14 for d in days_reg], "rfm_class"] = "新客"
    seg["predicted_ltv"] = 0.0
    seg["churn_prob"] = 0.0
    return seg[["user_id", "rfm_class", "recency_days", "frequency", "monetary",
                "lifetime_value", "predicted_ltv", "churn_prob"]]


def _build_funnel(events: pd.DataFrame, users: pd.DataFrame, orders: pd.DataFrame, end) -> pd.DataFrame:
    """裂变漏斗：浏览邀请页 → 分享 → 邀请注册 → 首单。

    漏斗只统计邀请渠道链路：首单仅计「邀请渠道用户的首单」，避免把全平台首单混入。
    """
    browse = events[events["event_name"] == "invite_click"].groupby("event_date")["user_id"].nunique()
    share = events[events["event_name"] == "invite_share"].groupby("event_date")["user_id"].nunique()
    register = users[users["register_channel"] == "invite"].groupby("register_date")["user_id"].nunique()
    invite_uid = set(users[users["register_channel"] == "invite"]["user_id"])
    first_ord = orders[
        orders["is_first_order"] & orders["user_id"].isin(invite_uid)
    ].groupby("order_date")["user_id"].nunique()

    rows = []
    for d in pd.date_range(users["register_date"].min(), end, freq="D"):
        dd = d.date()
        rows.append({"funnel_date": dd, "step": "浏览邀请页", "users": int(browse.get(dd, 0))})
        rows.append({"funnel_date": dd, "step": "分享链接", "users": int(share.get(dd, 0))})
        rows.append({"funnel_date": dd, "step": "邀请注册", "users": int(register.get(dd, 0))})
        rows.append({"funnel_date": dd, "step": "首单", "users": int(first_ord.get(dd, 0))})
    return pd.DataFrame(rows)
