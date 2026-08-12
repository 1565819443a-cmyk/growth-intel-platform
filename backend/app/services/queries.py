"""从数仓读取 DataFrame 的公共查询。

SQLite 下 pd.read_sql 会把 Date 列读成字符串，这里统一转 datetime，
服务层拿到即用。
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def _df(session: Session, sql: str, date_cols: list[str]) -> pd.DataFrame:
    df = pd.read_sql(text(sql), session.bind)
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c])
    return df


def load_user_seg(session: Session) -> pd.DataFrame:
    """ADS 用户分层（RFM + LTV + 流失概率）。"""
    return _df(session, "SELECT * FROM ads_user_seg", [])


def load_users(session: Session) -> pd.DataFrame:
    """用户维度表。"""
    return _df(session, "SELECT * FROM dim_user", ["register_date"])


def load_orders(session: Session) -> pd.DataFrame:
    """订单明细事实表。"""
    return _df(session, "SELECT * FROM dwd_order_fact", ["order_date"])


def load_events(session: Session) -> pd.DataFrame:
    """事件明细事实表（可指定事件）。"""
    return _df(session, "SELECT * FROM dwd_event_fact", ["event_date"])


def load_channel_daily(session: Session) -> pd.DataFrame:
    """DWS 渠道每日：spend / 曝光 / 点击 / 新增 / 订单 / GMV。"""
    return _df(session, "SELECT * FROM dws_channel_daily", ["stat_date"])


def load_invite_daily(session: Session) -> pd.DataFrame:
    """DWS 邀请每日。"""
    return _df(session, "SELECT * FROM dws_invite_daily", ["stat_date"])


def load_invites(session: Session) -> pd.DataFrame:
    """DWD 邀请事实表。"""
    return _df(session, "SELECT * FROM dwd_invite_fact", ["invite_date"])


def load_kpi_daily(session: Session) -> pd.DataFrame:
    """ADS 每日 KPI。"""
    return _df(session, "SELECT * FROM ads_kpi_daily ORDER BY stat_date", ["stat_date"])


def load_user_daily(session: Session) -> pd.DataFrame:
    """DWS 用户每日行为（留存/活跃用）。"""
    return _df(session, "SELECT * FROM dws_user_daily", ["stat_date", "register_date"])
