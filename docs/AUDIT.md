# 旧仓库审计与重构决策

## 保留

- 可复现模拟电商数据生成、ODS/DWD/DWS/ADS 命名与部分 RFM/MMM/裂变实现，作为领域高级模板参考。
- React + FastAPI 基础工程、ECharts 封装、部署目录与原 Git 历史。

## 替换

- 原接口按 Overview/Users/MMM/Growth/Report 写死且只认识单一数据库，替换为 Dataset Registry、Adapter、Semantic Mapping、Metric Engine、Quality Engine 和 Capability Resolver。
- 原前端固定五个增长页面，替换为数据集切换、数据源、字段映射、指标中心、自定义分析、质量与血缘页面。
- 原 README 把模型和 AI 报告放在核心位置，改为业务问题—数据来源—指标—加工—质量—结果—交付—限制—复现顺序。

旧的特定建模模块没有删除，避免破坏 Git 历史和有价值实现，但不再挂载到默认 API，也不被宣传为通用能力。

