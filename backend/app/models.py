"""数仓分层 ORM 模型：ODS → DWD → DWS → ADS。

命名沿用数仓惯例，表内字段用小写、时间统一用 Date 粒度（天）。
SQLite 与 PostgreSQL 通用。
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# --------------------------------------------------------------------------
# ODS 层：原始贴源数据
# --------------------------------------------------------------------------
class RawUser(Base):
    __tablename__ = "raw_users"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    register_channel: Mapped[str] = mapped_column(String(20))  # search/ads/social/invite/organic
    register_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    register_date: Mapped[date] = mapped_column(Date, index=True)
    city: Mapped[str] = mapped_column(String(40))
    device: Mapped[str] = mapped_column(String(10))  # ios/android
    inviter_id: Mapped[int] = mapped_column(BigInteger, nullable=True)


class RawEvent(Base):
    __tablename__ = "raw_events"
    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_name: Mapped[str] = mapped_column(String(20), index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)      # purchase 事件金额
    category: Mapped[str] = mapped_column(String(20), nullable=True)  # purchase 品类
    order_channel: Mapped[str] = mapped_column(String(10), nullable=True)


class RawOrder(Base):
    __tablename__ = "raw_orders"
    order_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    order_time: Mapped[datetime] = mapped_column(DateTime)
    order_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    order_channel: Mapped[str] = mapped_column(String(10))  # App/Web/H5
    is_first_order: Mapped[bool] = mapped_column(Boolean)


class RawChannelSpend(Base):
    __tablename__ = "raw_channel_spend"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spend_date: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(20))
    spend: Mapped[float] = mapped_column(Float)
    impressions: Mapped[int] = mapped_column(BigInteger)
    clicks: Mapped[int] = mapped_column(BigInteger)


class RawInvite(Base):
    __tablename__ = "raw_invites"
    invite_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, index=True)
    invitee_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=True)
    invite_time: Mapped[datetime] = mapped_column(DateTime)
    invite_date: Mapped[date] = mapped_column(Date, index=True)
    reward_tier: Mapped[int] = mapped_column(Integer)   # 档位：3/5/10 人
    reward_amount: Mapped[float] = mapped_column(Float)  # 该次邀请对应奖励
    accepted: Mapped[bool] = mapped_column(Boolean)


# --------------------------------------------------------------------------
# DWD 层：明细事实/维度
# --------------------------------------------------------------------------
class DwdEventFact(Base):
    __tablename__ = "dwd_event_fact"
    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_name: Mapped[str] = mapped_column(String(20), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String(20), nullable=True)
    order_channel: Mapped[str] = mapped_column(String(10), nullable=True)


class DwdOrderFact(Base):
    __tablename__ = "dwd_order_fact"
    order_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    order_date: Mapped[date] = mapped_column(Date, index=True)
    order_time: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(20))
    order_channel: Mapped[str] = mapped_column(String(10))
    is_first_order: Mapped[bool] = mapped_column(Boolean)


class DwdInviteFact(Base):
    __tablename__ = "dwd_invite_fact"
    invite_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, index=True)
    invitee_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=True)  # 未被接受则无注册用户
    invite_date: Mapped[date] = mapped_column(Date, index=True)
    invite_time: Mapped[datetime] = mapped_column(DateTime)
    reward_tier: Mapped[int] = mapped_column(Integer)
    reward_amount: Mapped[float] = mapped_column(Float)
    accepted: Mapped[bool] = mapped_column(Boolean)


class DimUser(Base):
    __tablename__ = "dim_user"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    register_channel: Mapped[str] = mapped_column(String(20), index=True)
    register_date: Mapped[date] = mapped_column(Date, index=True)
    city: Mapped[str] = mapped_column(String(40))
    device: Mapped[str] = mapped_column(String(10))
    inviter_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    invite_source: Mapped[str] = mapped_column(String(10))  # invited/organic


# --------------------------------------------------------------------------
# DWS 层：主题宽表（按天汇总）
# --------------------------------------------------------------------------
class DwsUserDaily(Base):
    __tablename__ = "dws_user_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    register_channel: Mapped[str] = mapped_column(String(20))
    register_date: Mapped[date] = mapped_column(Date)
    is_new: Mapped[bool] = mapped_column(Boolean)
    is_active: Mapped[bool] = mapped_column(Boolean)
    app_opens: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    add_to_cart: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[float] = mapped_column(Float, default=0.0)
    invite_clicks: Mapped[int] = mapped_column(Integer, default=0)
    invite_shares: Mapped[int] = mapped_column(Integer, default=0)


class DwsChannelDaily(Base):
    __tablename__ = "dws_channel_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    impressions: Mapped[int] = mapped_column(BigInteger, default=0)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[float] = mapped_column(Float, default=0.0)


class DwsInviteDaily(Base):
    __tablename__ = "dws_invite_daily"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    invites_sent: Mapped[int] = mapped_column(Integer, default=0)
    invites_accepted: Mapped[int] = mapped_column(Integer, default=0)
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)  # 当天经邀请注册
    new_user_gmv: Mapped[float] = mapped_column(Float, default=0.0)


# --------------------------------------------------------------------------
# ADS 层：应用层结果表
# --------------------------------------------------------------------------
class AdsKpiDaily(Base):
    __tablename__ = "ads_kpi_daily"
    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    gmv: Mapped[float] = mapped_column(Float, default=0.0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    paid_users: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_spend: Mapped[float] = mapped_column(Float, default=0.0)
    roas: Mapped[float] = mapped_column(Float, default=0.0)
    invite_accept_rate: Mapped[float] = mapped_column(Float, default=0.0)


class AdsUserSeg(Base):
    __tablename__ = "ads_user_seg"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rfm_class: Mapped[str] = mapped_column(String(12), index=True)  # 如 高价值/潜力/新客/流失预警...
    recency_days: Mapped[int] = mapped_column(Integer)
    frequency: Mapped[int] = mapped_column(Integer)
    monetary: Mapped[float] = mapped_column(Float)
    lifetime_value: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_ltv: Mapped[float] = mapped_column(Float, default=0.0)
    churn_prob: Mapped[float] = mapped_column(Float, default=0.0)


class AdsChannelRoi(Base):
    __tablename__ = "ads_channel_roi"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    spend: Mapped[float] = mapped_column(Float)
    gmv: Mapped[float] = mapped_column(Float)
    roas: Mapped[float] = mapped_column(Float)
    attributed_share: Mapped[float] = mapped_column(Float, default=0.0)  # 贡献占比(MMM)


class AdsGrowthFunnel(Base):
    __tablename__ = "ads_growth_funnel"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funnel_date: Mapped[date] = mapped_column(Date, index=True)
    step: Mapped[str] = mapped_column(String(20))  # browse/share/register/first_order
    users: Mapped[int] = mapped_column(Integer)
