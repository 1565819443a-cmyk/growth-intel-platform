#!/usr/bin/env python
"""灌数脚本：生成模拟数据 → 建数仓分层 → 入库。

用法：
    cd backend && .venv/bin/python scripts/seed_data.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, engine  # noqa: E402
from app.services import warehouse  # noqa: E402
from app import models  # noqa: E402,F401  (确保所有表已注册到 Base.metadata)


def main():
    print("== 重建表结构 ==")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("表已创建:", sorted(Base.metadata.tables))

    print("\n== 构建数仓 ==")
    stats = warehouse.build_warehouse(engine)
    print("\n== 灌数完成 ==")
    for k, v in stats.items():
        print(f"  {k}: {v:,}")

    print("\n== 数据抽查 ==")
    with engine.begin() as conn:
        from sqlalchemy import text
        for q, label in [
            ("SELECT count(*) FROM raw_users", "raw_users"),
            ("SELECT count(*) FROM raw_events", "raw_events"),
            ("SELECT count(*) FROM raw_orders", "raw_orders"),
            ("SELECT count(*) FROM raw_invites", "raw_invites"),
            ("SELECT count(*) FROM dwd_event_fact", "dwd_event_fact"),
            ("SELECT count(*) FROM dws_user_daily", "dws_user_daily"),
            ("SELECT count(*) FROM dws_channel_daily", "dws_channel_daily"),
            ("SELECT count(*) FROM ads_kpi_daily", "ads_kpi_daily"),
            ("SELECT count(*) FROM ads_growth_funnel", "ads_growth_funnel"),
            # round(x*10)/10.0 写法兼容 SQLite 与 Postgres（后者无 round(x, n) 双参形式）
            ("SELECT round(sum(gmv)*10)/10.0, round(sum(total_spend)*10)/10.0, "
             "round(sum(gmv)/nullif(sum(total_spend),0)*100)/100.0 "
             "FROM ads_kpi_daily", "ads_kpi_daily (GMV, spend, ROAS)"),
            ("SELECT rfm_class, count(*) FROM ads_user_seg GROUP BY rfm_class ORDER BY 2 DESC", "RFM 分层"),
        ]:
            try:
                rows = conn.execute(text(q)).fetchall()
            except Exception as e:  # noqa: BLE001
                print(f"  [{label}] 查询失败: {e}")
                conn.rollback()  # 单条失败不影响后续抽查
                continue
            print(f"  [{label}]", rows[:6])


if __name__ == "__main__":
    main()
