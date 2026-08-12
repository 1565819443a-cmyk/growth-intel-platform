"""模拟数据生成器（固定随机种子，可复现）。

生成 6 个月的跨境电商/社交裂变场景数据：
- 用户注册（渠道：搜索/广告/社媒/邀请/自然）
- 事件流（app_open / view_item / add_to_cart / purchase / invite_click / invite_share）
- 渠道投放（spend / impressions / clicks）
- 裂变邀请链路（inviter → invitee、激励阶梯 3/5/10 人档）
- 订单（金额、品类、下单渠道）

返回 pandas DataFrame，由 warehouse.py 落库。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

# 固定种子，保证结果可复现
np.random.seed(42)

# --------------------------------------------------------------------------
# 业务参数
# --------------------------------------------------------------------------
CHANNELS = ["search", "ads", "social", "invite", "organic"]
CHANNEL_WEIGHTS = {"search": 0.22, "ads": 0.26, "social": 0.18, "invite": 0.19, "organic": 0.15}
# 国际电商城市（含海外）
CITIES = ["上海", "北京", "深圳", "广州", "杭州", "成都",
          "New York", "London", "Tokyo", "Singapore", "Dubai", "Paris", "Sydney", "Seoul"]
CITY_WEIGHTS = [0.16, 0.12, 0.10, 0.08, 0.07, 0.06,
                0.10, 0.08, 0.08, 0.06, 0.03, 0.03, 0.02, 0.01]
DEVICES = ["ios", "android"]
DEVICE_WEIGHTS = [0.55, 0.45]
CATEGORIES = ["潮流鞋服", "箱包配饰", "腕表珠宝", "美妆个护", "数码3C"]
ORDER_CHANNELS = ["App", "H5", "Web"]
ORDER_CHANNEL_WEIGHTS = [0.68, 0.22, 0.10]

# 激励阶梯：达到的邀请人数档 → 奖励金额（元）
TIER_REWARD = {3: 20.0, 5: 40.0, 10: 100.0}
TIER_FOR_INVITE = [3, 3, 3, 5, 5, 10, 10, 10, 10, 10]  # 第 k(1基) 次邀请对应的档位

# 投放成本参数（用于 MMM 输入）
SPEND_BASE = {"search": 12000.0, "ads": 15000.0, "social": 9000.0, "invite": 2000.0, "organic": 0.0}
CTR = {"search": 0.028, "ads": 0.012, "social": 0.035, "invite": 0.08, "organic": 0.0}

# 渠道真实投放效率（每单位 spend 对购买的拉动，用于在订单生成中注入媒体效应，
# 让 MMM 有可恢复的信号：invite 最高效 → 形成「预算错配、可重分配」的业务故事）
SPEND_EFFICACY = {"search": 0.5, "ads": 0.4, "social": 0.6, "invite": 1.5, "organic": 0.0}

# 媒体直接归因订单（MMM 强信号）：n_orders = ATTR_MAX[c] * Hill(eff_spend_c, S=2, K=ATTR_K[c])
# 效率排序 invite >> social > search >> ads（ads 花最多但已饱和、效率最低 → 预算错配故事）
ATTR_MAX = {"search": 200.0, "ads": 140.0, "social": 175.0, "invite": 150.0}
ATTR_K = {"search": 28000.0, "ads": 36000.0, "social": 18000.0, "invite": 4000.0}
ATTR_CARRY_ALPHA = 0.35  # 媒体 carryover 指数衰减系数


def _dates(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _invite_accept_rate(reg_t, start):
    """邀请接受率随注册月龄攀升：早期用户约 0.32，随产品成熟逐步提升到 ~0.62。

    制造「增长曲线越来越好」的故事：越晚注册的用户，分享出的邀请更容易被接受。
    """
    reg_t = reg_t.to_pydatetime() if hasattr(reg_t, "to_pydatetime") else reg_t
    months = (reg_t - datetime.combine(start, time(0))).days / 30.0
    return float(np.clip(0.32 + 0.04 * months, 0.30, 0.62))


# --------------------------------------------------------------------------
# 用户
# --------------------------------------------------------------------------
def gen_users(start: date, end: date, n_users: int) -> pd.DataFrame:
    span_days = (end - start).days + 1
    days = np.array([start + timedelta(days=i) for i in range(span_days)])
    # 注册量随时间增长 + 周内季节性
    t = np.arange(span_days)
    day_w = 0.6 + 0.4 * (t / max(span_days, 1)) + 0.15 * (np.mod(t, 7) < 2)  # 周末略高
    day_w = day_w / day_w.sum()

    n_core = int(n_users * (1 - CHANNEL_WEIGHTS["invite"]))
    # 第一步：非邀请渠道用户（search/ads/social/organic）
    core_channel = np.random.choice(
        ["search", "ads", "social", "organic"], size=n_core,
        p=[CHANNEL_WEIGHTS[c] / (1 - CHANNEL_WEIGHTS["invite"]) for c in ["search", "ads", "social", "organic"]],
    )
    core_day = np.random.choice(span_days, size=n_core, p=day_w)
    core_hour = np.random.normal(15, 4, size=n_core).clip(0, 23)
    core_time = np.array(
        [datetime.combine(days[d], time(hour=int(h))) for d, h in zip(core_day, core_hour)]
    )

    core_df = pd.DataFrame({
        "register_time": core_time,
        "register_channel": core_channel,
    }).sort_values("register_time").reset_index(drop=True)
    core_df["user_id"] = np.arange(1, n_core + 1)
    core_df["_orig_uid"] = core_df["user_id"]  # 重编号前的原始核心用户 id，用于 invite 归因 remap
    core_df["inviter_id"] = np.nan

    # 第二步：从核心用户中选出分享者（发邀请链接的人）
    # 分享倾向：社媒渠道最高，其余渠道低（收敛分享者池，避免「人人都发邀请」）
    share_prop = core_df["register_channel"].map(
        {"search": 0.12, "ads": 0.10, "social": 0.40, "organic": 0.15}
    ).values
    # 已留存一段时间才会发邀请：注册 >= 5 天
    eligible = core_df[
        core_df["register_time"] <= pd.Timestamp(end - timedelta(days=5))
    ].index.values
    inviter_pool = core_df.loc[
        np.random.random(len(core_df)) < share_prop
    ].index.values
    inviter_pool = np.intersect1d(inviter_pool, eligible)
    inviter_pool = [int(i) for i in inviter_pool]

    # 第三步：生成邀请，被接受 → 邀请渠道新用户
    invites = []  # (inviter_user_id, invite_time, accepted, tier, reward)
    n_invite_users = n_users - n_core
    accepted_regs = []  # (invite_row_idx, register_time, inviter_id)

    def invite_count(uid):
        # 邀请数量与分享倾向正相关（社媒渠道用户更爱分享）
        ch = core_df.loc[uid, "register_channel"]
        base = 9 if ch == "social" else 4
        return max(0, int(np.random.poisson(base * 1.2)))

    end_dt = datetime.combine(end, time(23, 59, 59))
    for uid in inviter_pool:
        cnt = invite_count(uid)
        if cnt <= 0:
            continue
        reg_t = core_df.loc[uid, "register_time"]
        reg_t = reg_t.to_pydatetime() if hasattr(reg_t, "to_pydatetime") else reg_t
        for k in range(1, cnt + 1):
            # 邀请时间在注册后的 2~10 天内（集中邀请窗口，模拟活动期邀请高峰）
            offset = np.random.randint(2, 11)
            inv_t = reg_t + timedelta(days=offset)
            if inv_t > end_dt:
                break
            inv_t = inv_t.replace(hour=int(np.clip(np.random.normal(20, 3), 10, 23)))
            tier = TIER_FOR_INVITE[min(k - 1, len(TIER_FOR_INVITE) - 1)]
            reward = TIER_REWARD[tier]
            # 接受率随注册月龄攀升（增长故事：早期 0.32 → 后期 0.62）
            accepted = np.random.random() < _invite_accept_rate(reg_t, start)
            # 存原始核心 user_id（int(uid)+1）；重编号后再 remap 到全局 id
            invites.append((int(uid) + 1, inv_t, accepted, tier, reward))
            if accepted:
                rt = inv_t + timedelta(minutes=int(np.random.randint(5, 400)))
                if rt > end_dt:
                    rt = end_dt
                accepted_regs.append((len(invites) - 1, rt, int(uid) + 1))

    invites_df = pd.DataFrame(invites, columns=["inviter_id", "invite_time", "accepted", "tier", "reward"])

    # 邀请渠道用户 = 被接受邀请的注册。
    # 严格保证「被接受的邀请数」==「邀请渠道注册用户数」：
    # 被接受邀请多于目标时随机保留 n_invite_users 条，并把 invites_df 的 accepted 标记同步修正。
    if len(accepted_regs) > n_invite_users:
        keep = set(np.random.choice(len(accepted_regs), size=n_invite_users, replace=False).tolist())
        accepted_regs = [accepted_regs[i] for i in sorted(keep)]
    kept_idx = {r[0] for r in accepted_regs}
    invites_df["accepted"] = invites_df.index.isin(kept_idx)

    invite_df = pd.DataFrame(
        [(rt, int(uid), _idx + 1) for _idx, rt, uid in accepted_regs],
        columns=["register_time", "inviter_id", "via_invite_id"],
    )
    invite_df["register_channel"] = "invite"
    n_invite_actual = len(invite_df)

    full_df = pd.concat([core_df, invite_df], ignore_index=True)
    full_df = full_df.sort_values("register_time").reset_index(drop=True)
    # 重新编号（保证 inviter < invitee 且注册时间有序）
    full_df["user_id"] = np.arange(1, len(full_df) + 1)
    full_df["register_date"] = full_df["register_time"].dt.date

    # 重编号后核心用户 id 全局移位：把 inviter_id（原始核心 id）映射到新 id，
    # 否则邀请链路会错误归因到「恰好落在旧索引值上的用户」。
    core_new = full_df.loc[full_df["register_channel"] != "invite", "user_id"].values
    remap = dict(zip(np.arange(1, n_core + 1), core_new))
    full_df["inviter_id"] = full_df["inviter_id"].map(remap)
    invites_df["inviter_id"] = invites_df["inviter_id"].map(remap)
    full_df = full_df.drop(columns=["_orig_uid"])

    # 城市 / 设备
    full_df["city"] = np.random.choice(CITIES, size=len(full_df), p=CITY_WEIGHTS)
    full_df["device"] = np.random.choice(DEVICES, size=len(full_df), p=DEVICE_WEIGHTS)
    full_df = full_df[["user_id", "register_channel", "register_time", "register_date",
                       "city", "device", "inviter_id", "via_invite_id"]]

    return full_df, invites_df


# --------------------------------------------------------------------------
# 事件流 + 订单
# --------------------------------------------------------------------------
def gen_events_and_orders(users: pd.DataFrame, end: date, lift_map: dict | None = None,
                          attribution: dict | None = None) -> pd.DataFrame:
    """为每个用户生成生命周期内的活跃日与事件；购买事件同时产出订单。

    lift_map:     {date: lift}，媒体拉动乘子，注入后购买概率 ∝ lift。
    attribution:  {date: {channel: int}}，媒体直接归因订单数，追加为强媒体信号。
    """
    rows = []        # 事件行
    orders = []      # 订单行
    event_id = 1
    order_id = 1

    # 用户行为参数
    engage = np.random.choice([0.5, 1.0, 1.6], size=len(users), p=[0.25, 0.55, 0.20])  # 活跃度
    # 双组件留存：30% 粘性用户（全程在网、不衰减），70% 快速流失（tau~15 天）。
    # 目的：观察期末 recency<=30 的活跃用户约占 55%，同时让沉默用户形成真实「流失」结构。
    sticky = np.random.random(len(users)) < 0.30
    tau = np.empty(len(users))
    tau[sticky] = 1e9  # 粘性用户：p_active 恒为 max_ret
    n_nonsticky = int((~sticky).sum())
    tau[~sticky] = np.random.gamma(3.0, 5.0, size=n_nonsticky).clip(10, 45)
    max_ret = np.random.uniform(0.55, 0.85, size=len(users))
    lifespan = (np.random.gamma(2.0, 28.0, size=len(users))).clip(1, (end - users["register_date"].min()).days).astype(int)
    lifespan[sticky] = (end - users["register_date"].min()).days  # 粘性用户全程在网
    # 购买倾向：20% 浏览型用户（从不购买 → 沉睡池），80% 正常买家。
    # 避免「全员购买」导致流失预警占比畸高（真实 App 大部分沉默用户从未交易）。
    buyer_intent = np.random.choice([0.0, 1.0], size=len(users), p=[0.20, 0.80])

    # churn 噪声：让流失模型 AUC 从 ~0.99 落回 0.65-0.85 合理区间。
    #  - is_dark（45%）：用户观察期末「断电」，最后活跃日提前到 dark_day 天之后，
    #    制造「活跃画像相似但结局不同」的特征重叠，拉低 AUC。
    #  - is_ret（40%）：用户观察期末「回归」，在最后 30 天内补一个活跃日，
    #    让标签分布更接近真实（部分沉默用户在窗口末仍活跃）。
    is_dark = np.random.random(len(users)) < 0.45
    dark_day = np.random.randint(20, 101, size=len(users)).astype(int)  # 断电发生在注册后 20~100 天
    is_ret = np.random.random(len(users)) < 0.40
    end_dt = datetime.combine(end, time(23, 59, 59))

    is_invite_user = (users["register_channel"].values == "invite")

    for i, u in enumerate(users.itertuples()):
        reg_dt = u.register_time.to_pydatetime()
        life = int(lifespan[i])
        days = np.arange(life)
        p_active = max_ret[i] * np.exp(-days / tau[i])
        active = np.random.random(life) < p_active
        active_days = np.where(active)[0]
        if is_dark[i]:
            # 断电：只保留注册后 dark_day 天之前的活跃日
            active_days = active_days[active_days < dark_day[i]]
        if len(active_days) == 0:
            continue
        # 回归：在观察期末补一个活跃日（保证 recency <= 30），模拟「回流用户」
        ret_day = None
        if is_ret[i]:
            # 找一个落在 [end-30, end] 的活跃日（相对注册日的 day 索引）
            lo = int((datetime.combine(end - timedelta(days=30), time(0)) - reg_dt).days)
            hi = int((end_dt - reg_dt).days)
            if hi > lo:
                ret_day = int(np.random.randint(lo, hi + 1))
                if ret_day in active_days:
                    ret_day = None

        e = engage[i]
        for d in active_days:
            ddate = (reg_dt + timedelta(days=int(d))).date()
            if ddate > end:
                break
            # 打开 App
            for _ in range(1 + int(np.random.poisson(0.5 * e))):
                rows.append((event_id, u.user_id, "app_open", ddate, None, None, None, None)); event_id += 1
            # 浏览
            n_view = int(np.random.poisson(1.4 * e))
            for _ in range(n_view):
                rows.append((event_id, u.user_id, "view_item", ddate, int(np.random.randint(1, 2000)), None, None, None)); event_id += 1
            # 加购
            if np.random.random() < 0.22 * e:
                rows.append((event_id, u.user_id, "add_to_cart", ddate, int(np.random.randint(1, 2000)), None, None, None)); event_id += 1
                # 下单（媒体拉动：高投放日购买概率更高，注入 MMM 可恢复信号）
                lift = lift_map.get(ddate, 1.0) if lift_map else 1.0
                if np.random.random() < 0.5 * lift * buyer_intent[i]:
                    amount = float(np.random.lognormal(5.2, 0.9))
                    amount = round(max(20, min(20000, amount)) * (0.9 + 0.2 * lift), 2)
                    category = str(np.random.choice(CATEGORIES))
                    o_ch = str(np.random.choice(ORDER_CHANNELS, p=ORDER_CHANNEL_WEIGHTS))
                    ts = ddate  # 事件时间
                    rows.append((event_id, u.user_id, "purchase", ddate, order_id, amount, category, o_ch)); event_id += 1
                    orders.append((order_id, u.user_id, ddate, amount, category, o_ch))
                    order_id += 1
            # 裂变动作：邀请渠道用户或高活跃用户更可能点邀请页
            if is_invite_user[i] or np.random.random() < 0.25 * e:
                if np.random.random() < 0.5:
                    rows.append((event_id, u.user_id, "invite_click", ddate, None, None, None, None)); event_id += 1
                if np.random.random() < 0.15 * e:
                    rows.append((event_id, u.user_id, "invite_share", ddate, None, None, None, None)); event_id += 1

        # 回归日：补一次 App 打开 + 浏览，让 recency <= 30（观察期末仍活跃）
        if ret_day is not None:
            rddate = (reg_dt + timedelta(days=int(ret_day))).date()
            if rddate <= end:
                for _ in range(1 + int(np.random.poisson(0.5 * e))):
                    rows.append((event_id, u.user_id, "app_open", rddate, None, None, None, None)); event_id += 1
                for _ in range(int(np.random.poisson(1.4 * e))):
                    rows.append((event_id, u.user_id, "view_item", rddate, int(np.random.randint(1, 2000)), None, None, None)); event_id += 1

    # ---- 媒体直接归因订单（追加到自然行为订单上，注入 MMM 可恢复信号） ----
    if attribution:
        open_rows = [r for r in rows if r[2] == "app_open"]
        # 媒体直接归因订单只派发给正常买家（浏览型用户不参与购买）
        buyer_uids = set(users.iloc[np.where(buyer_intent > 0)[0]]["user_id"].tolist())
        active_pool: dict = {}
        for _eid, _uid, _name, ddate, *_rest in open_rows:
            if _uid in buyer_uids:
                active_pool.setdefault(ddate, []).append(_uid)
        for ddate, ch_counts in attribution.items():
            pool = active_pool.get(ddate)
            if not pool:
                continue
            for ch, cnt in ch_counts.items():
                for _ in range(int(cnt)):
                    uid = int(np.random.choice(pool))
                    amount = float(np.random.lognormal(5.2, 0.9))
                    amount = round(max(20, min(20000, amount)), 2)
                    category = str(np.random.choice(CATEGORIES))
                    o_ch = str(np.random.choice(ORDER_CHANNELS, p=ORDER_CHANNEL_WEIGHTS))
                    rows.append((event_id, uid, "purchase", ddate, order_id, amount, category, o_ch)); event_id += 1
                    orders.append((order_id, uid, ddate, amount, category, o_ch))
                    order_id += 1

    events = pd.DataFrame(rows, columns=[
        "event_id", "user_id", "event_name", "event_date", "item_id", "amount", "category", "order_channel"
    ])
    ord_df = pd.DataFrame(orders, columns=["order_id", "user_id", "order_date", "amount", "category", "order_channel"])
    # 首单标记：每个用户按时间最早的一笔订单为「首单」。
    # 不能用 duplicated(keep='first')——它按 order_date 值判重，同用户不同日期的多笔订单会被全部标为首单。
    ord_df["is_first_order"] = False
    first_idx = ord_df.groupby("user_id")["order_date"].idxmin()
    ord_df.loc[first_idx, "is_first_order"] = True
    return events, ord_df


# --------------------------------------------------------------------------
# 渠道投放
# --------------------------------------------------------------------------
def gen_channel_spend(start: date, end: date) -> pd.DataFrame:
    """各渠道差异化投放模式：

    - search：成熟渠道，份额缓慢下滑（-35% 线性）
    - ads    ：新渠道，快速扩张（+60% 线性）
    - social ：周期波动（sin 15 天）
    - invite ：奖励成本尖峰波动（sin 9 天，幅度大）
    四种模式互不共线，保证 MMM 能分离出各渠道效应。
    """
    rows = []
    t = 0
    span = (end - start).days + 1
    for d in _dates(start, end):
        dow = d.weekday()
        weekend = 1.5 if dow >= 5 else 1.0
        x = t / max(span - 1, 1)
        for ch in ["search", "ads", "social", "invite", "organic"]:
            if ch == "organic":
                spend = 0.0
            elif ch == "search":
                spend = SPEND_BASE[ch] * (1 - 0.35 * x) * (1 + 0.25 * np.sin(t / 21.0)) \
                    * weekend * np.random.uniform(0.85, 1.2)
            elif ch == "ads":
                spend = SPEND_BASE[ch] * (1 + 0.6 * x) * (1 + 0.4 * np.sin(t / 30.0)) \
                    * weekend * np.random.uniform(0.85, 1.2)
            elif ch == "social":
                spend = SPEND_BASE[ch] * (1 + 0.3 * np.sin(t / 10.0)) * weekend * np.random.uniform(0.85, 1.2)
            else:  # invite
                spend = SPEND_BASE[ch] * (1 + 0.6 * np.sin(t / 7.5)) * weekend * np.random.uniform(0.85, 1.2)
            spend = round(spend, 2)
            impressions = int(spend / np.random.uniform(3.0, 6.0) * 1000)  # CPM 3~6 元
            clicks = int(impressions * CTR[ch] * np.random.uniform(0.85, 1.15))
            rows.append((d, ch, spend, impressions, clicks))
        t += 1
    return pd.DataFrame(rows, columns=["spend_date", "channel", "spend", "impressions", "clicks"])


def get_media_lift(channel_spend: pd.DataFrame) -> dict:
    """每日媒体拉动系数：对非 organic 渠道 spend 做加权指数衰减（carryover）后饱和。

    返回 {date: lift}，lift ∈ [1.0, ~1.7]，注入订单生成时乘到购买概率上，
    使 GMV 对渠道投放产生真实、带滞后、递减的响应（invite 效率最高）。
    """
    spend = channel_spend[channel_spend["channel"] != "organic"].copy()
    spend["spend_date"] = pd.to_datetime(spend["spend_date"])
    pivot = spend.pivot_table(index="spend_date", columns="channel",
                              values="spend", aggfunc="sum").fillna(0.0)
    eff = pd.Series(0.0, index=pivot.index)
    for ch in list(SPEND_EFFICACY):
        if ch in pivot.columns:
            carry = pivot[ch].ewm(alpha=0.3).mean().fillna(0.0)  # 指数衰减 carryover
            eff = eff + SPEND_EFFICACY[ch] * carry
    sat = 0.7 * (eff / (eff + 12000.0))  # Hill 式饱和，幅度上限 0.7
    lift = 1.0 + sat
    return {d.date(): float(v) for d, v in lift.items()}


def get_media_attribution(channel_spend: pd.DataFrame) -> dict:
    """媒体直接归因订单数：{date: {channel: int 订单数}}。

    对每日每渠道 spend 做指数衰减 carryover → Hill 饱和 → 乘以 ATTR_MAX。
    这部分订单是「媒体带来的购买」，注入后 MMM 能分离出各渠道真实效应。
    """
    spend = channel_spend[channel_spend["channel"] != "organic"].copy()
    spend["spend_date"] = pd.to_datetime(spend["spend_date"])
    pivot = spend.pivot_table(index="spend_date", columns="channel",
                              values="spend", aggfunc="sum").fillna(0.0)

    attribution: dict = {}
    for ch in list(ATTR_MAX):
        if ch not in pivot.columns:
            continue
        carry = pivot[ch].ewm(alpha=ATTR_CARRY_ALPHA).mean().fillna(0.0)
        x = carry.values
        hill = x ** 2 / (x ** 2 + ATTR_K[ch] ** 2 + 1e-9)
        n = ATTR_MAX[ch] * hill
        for d, val in zip(pivot.index, n):
            ddate = d.date()
            cnt = int(val) + (1 if np.random.random() < (val - int(val)) else 0)
            if cnt > 0:
                attribution.setdefault(ddate, {})[ch] = cnt
    return attribution
