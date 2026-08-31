# 指标治理说明

指标配置包含中文名、聚合方式、字段、默认过滤、负责人、版本与单位。目前真实执行支持 count、distinct count、sum、average、ratio、derived expression、按日/周/月分组、累计和环比。

安全边界：数据集 ID 必须命中注册文件；指标必须命中配置；维度与过滤字段必须位于白名单且真实存在；标识符只接受安全字符；值使用参数绑定；前端没有提交 SQL 的接口。后端返回生成 SQL 仅用于面试讲解和审计。

HMDA 拒绝率配置为 `action_taken=3 / action_taken in (1,2,3)`，并不会套用电商“转化率”；GA4 收入和 HMDA 发放金额只是同为 amount 语义角色，业务名称与公式仍独立治理。

