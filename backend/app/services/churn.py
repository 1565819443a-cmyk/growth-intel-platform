"""流失预警：GradientBoosting 分类器。

特征：购买频次 / 客单价 / 活跃天数 / 打开次数 / 渠道 / 设备 / 注册时长。
目标：观察期末已流失（recency >= 30 天且注册满 30 天）。
注意：特征刻意不含 recency_days，避免「标签直接当特征」的目标泄漏；
模型从历史行为画像判断流失概率，风险名单再叠加「当前已沉默」规则。
输出：全量用户流失概率、Top 风险名单、特征重要性、模型指标。
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from .queries import load_user_seg, load_user_daily, load_users


CHURN_RECENCY = 30      # 连续 N 天无活跃视为流失
MIN_AGE_DAYS = 30       # 注册满 N 天才纳入训练标签
AT_RISK_PROB = 0.50     # 模型流失概率阈值，只有高置信度沉默用户进风险名单


def churn_model(session, writeback: bool = False) -> Dict[str, Any]:
    seg = load_user_seg(session)
    users = load_users(session)
    daily = load_user_daily(session)

    if seg.empty:
        return {"error": "无用户分层数据"}

    # 行为聚合：活跃天数 / 打开次数
    act = daily.groupby("user_id").agg(
        active_days=("stat_date", "nunique"),
        app_opens=("app_opens", "sum"),
    ).reset_index()

    feat = seg.merge(users[["user_id", "register_channel", "device", "register_date"]], on="user_id", how="left") \
              .merge(act, on="user_id", how="left")
    feat["active_days"] = feat["active_days"].fillna(0)
    feat["app_opens"] = feat["app_opens"].fillna(0)

    end = pd.Timestamp(feat["register_date"].max()) if "register_date" in feat else pd.Timestamp.now()
    age = (end - pd.to_datetime(feat["register_date"])).dt.days
    feat["age_days"] = age
    feat["log_monetary"] = np.log1p(feat["monetary"].astype(float))

    # 标签：已流失（recency >= CHURN_RECENCY）
    labeled = feat[(feat["age_days"] >= MIN_AGE_DAYS)].copy()
    y = (labeled["recency_days"] >= CHURN_RECENCY).astype(int)

    # 特征：不含 recency_days（避免目标泄漏）
    cat_cols = ["register_channel", "device"]
    X = labeled[["frequency", "log_monetary",
                 "active_days", "app_opens", "age_days"]].copy()
    for c in cat_cols:
        X = pd.concat([X, pd.get_dummies(labeled[c], prefix=c)], axis=1)

    # 用全体已标记样本训练（有监督 + 简单校验）
    X_tr, X_va, y_tr, y_va = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = GradientBoostingClassifier(
        n_estimators=120, max_depth=3, learning_rate=0.08, subsample=0.9, random_state=42
    )
    clf.fit(X_tr, y_tr)

    # 全量预测
    full = seg.merge(users[["user_id", "register_channel", "device", "register_date"]], on="user_id", how="left") \
              .merge(act, on="user_id", how="left")
    full["active_days"] = full["active_days"].fillna(0)
    full["app_opens"] = full["app_opens"].fillna(0)
    full["log_monetary"] = np.log1p(full["monetary"].astype(float))
    full["age_days"] = (end - pd.to_datetime(full["register_date"])).dt.days
    X_all = pd.get_dummies(full, columns=["register_channel", "device"])
    keep = ["frequency", "log_monetary", "active_days", "app_opens", "age_days"] \
        + [c for c in X_all.columns if c.startswith("register_channel_") or c.startswith("device_")]
    X_all = X_all[keep].reindex(columns=X.columns, fill_value=0)
    prob = clf.predict_proba(X_all)[:, 1]

    prob_df = pd.DataFrame({"user_id": seg["user_id"], "churn_prob": prob})
    if writeback:
        from sqlalchemy import text
        session.execute(
            text("UPDATE ads_user_seg SET churn_prob = :v WHERE user_id = :u"),
            [{"v": float(v), "u": int(u)} for v, u in zip(prob_df["churn_prob"], prob_df["user_id"])],
        )
        session.commit()

    # 风险名单：当前已沉默 + 模型高置信度流失（避免全员进名单）
    risk = prob_df.merge(seg.drop(columns=["churn_prob"], errors="ignore"), on="user_id", how="left") \
                  .merge(users[["user_id", "register_channel", "city"]], on="user_id", how="left")
    risk = risk[
        (risk["recency_days"] >= CHURN_RECENCY) & (risk["churn_prob"] >= AT_RISK_PROB)
    ].sort_values("churn_prob", ascending=False)
    at_risk = [
        {
            "user_id": int(r.user_id),
            "churn_prob": round(float(r.churn_prob), 3),
            "recency_days": int(r.recency_days),
            "frequency": int(r.frequency),
            "monetary": round(float(r.monetary), 1),
            "channel": r.register_channel,
            "city": r.city,
        }
        for r in risk.head(50).itertuples()
    ]

    auc = roc_auc_score(y_va, clf.predict_proba(X_va)[:, 1]) if len(set(y_va)) > 1 else 0.0
    feat_imp = sorted(
        zip(X.columns, clf.feature_importances_), key=lambda t: -t[1]
    )

    return {
        "churn_recency_days": CHURN_RECENCY,
        "trained_users": int(len(X)),
        "churn_rate": round(float(y.mean()), 3),
        "auc": round(float(auc), 3),
        "at_risk_count": int(len(risk)),
        "feature_importance": [
            {"feature": f, "importance": round(float(v), 4)} for f, v in feat_imp[:8]
        ],
        "at_risk_top": at_risk,
    }
