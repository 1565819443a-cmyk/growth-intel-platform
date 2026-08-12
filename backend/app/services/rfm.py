"""RFM 分层分析：分群规模、画像、价值与 Top 名单。

复用 ADS 已计算好的 ads_user_seg.rfm_class（在数仓构建时生成），
这里做服务层的二次加工：分群画像 + 留存对比 + 高危清单。
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .queries import load_user_seg


def segment_overview(session) -> Dict[str, Any]:
    seg = load_user_seg(session)
    seg["monetary"] = pd.to_numeric(seg["monetary"], errors="coerce").fillna(0.0)
    seg["recency_days"] = pd.to_numeric(seg["recency_days"], errors="coerce").fillna(0).astype(int)

    total = int(len(seg))
    classes = ["高价值", "高潜力", "新客", "一般", "流失预警", "沉睡"]

    dist = []
    for c in classes:
        sub = seg[seg["rfm_class"] == c]
        dist.append({
            "name": c,
            "count": int(len(sub)),
            "share": round(len(sub) / total * 100, 1) if total else 0.0,
            "avg_recency_days": float(sub["recency_days"].mean()) if len(sub) else 0.0,
            "avg_frequency": float(sub["frequency"].mean()) if len(sub) else 0.0,
            "avg_monetary": round(float(sub["monetary"].mean()), 1) if len(sub) else 0.0,
        })

    # 分群价值构成：各群 GMV 占大盘比例
    total_monetary = float(seg["monetary"].sum()) or 1.0
    for d in dist:
        sub = seg[seg["rfm_class"] == d["name"]]
        d["gmv_share"] = round(float(sub["monetary"].sum()) / total_monetary * 100, 1)

    # Top 高价值用户（供表格展示）
    top = (seg[seg["rfm_class"].isin(["高价值", "高潜力"])]
           .sort_values("monetary", ascending=False)
           .head(50))
    top_list = [
        {
            "user_id": int(r.user_id),
            "rfm_class": r.rfm_class,
            "recency_days": int(r.recency_days),
            "frequency": int(r.frequency),
            "monetary": round(float(r.monetary), 1),
            "predicted_ltv": round(float(r.predicted_ltv or 0.0), 1),
        }
        for r in top.itertuples()
    ]

    return {
        "total_users": total,
        "segments": dist,
        "top_users": top_list,
    }
