# 领域项目接入契约

每个领域项目独立运行并导出 ZSTD Parquet。通用平台只依赖标准结果，不依赖领域项目内部数据库。

```bash
python backend/scripts/import_contracts.py \
  --ga4 ../ga4-ecommerce-data-platform/data/platform/ga4_events.parquet \
  --hmda ../hmda-credit-analytics-platform/data/platform/hmda_applications.parquet
```

GA4 最小字段：`event_timestamp,event_name,user_pseudo_id,session_id,transaction_id,purchase_revenue,source,medium,campaign`。HMDA 最小字段：`application_id,institution_id,activity_year,action_taken,loan_amount,county_code,product_type`。物理字段不要求相同，由各自 `backend/configs/datasets/*.yaml` 映射成 user/application/time/amount/channel/region/status 等角色。

缺失导入文件时数据集仍显示在注册中心，但状态为待导入、连接测试返回明确路径；独立演示始终可使用仓库内的小型模拟电商数据。

