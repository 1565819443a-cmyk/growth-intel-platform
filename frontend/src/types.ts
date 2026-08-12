/* 与后端 API 返回结构对齐的类型定义 */

export interface Period {
  start: string;
  end: string;
}

export interface OverviewSummary {
  total_gmv: number;
  total_orders: number;
  total_users: number;
  mau: number;
  aov: number;
  total_spend: number;
  roas: number;
}

export interface ChannelKpi {
  channel: string;
  spend: number;
  gmv: number;
  roas: number;
}

export interface TrendPoint {
  date: string;
  gmv: number;
  orders: number;
  new_users: number;
  active_users: number;
  roas: number;
}

export interface Overview {
  period: Period;
  summary: OverviewSummary;
  channels: ChannelKpi[];
  trend: TrendPoint[];
}

/* ---------------- 用户分层 ---------------- */

export interface UserSegment {
  name: string;
  count: number;
  share: number;
  avg_recency_days: number;
  avg_frequency: number;
  avg_monetary: number;
  gmv_share: number;
}

export interface TopUser {
  user_id: number;
  rfm_class: string;
  recency_days: number;
  frequency: number;
  monetary: number;
  predicted_ltv: number;
}

export interface UserSegments {
  total_users: number;
  segments: UserSegment[];
  top_users: TopUser[];
}

export interface CohortRow {
  cohort: string;
  size: number;
  rates: number[];
  values: number[];
}

export interface Cohort {
  horizon_weeks: number;
  weeks: number[];
  retention: CohortRow[];
  ltv: CohortRow[];
}

export interface LtvBucket {
  bucket: string;
  count: number;
}

export interface LtvPrediction {
  horizon_days: number;
  observation_end: string;
  model_users: number;
  avg_predicted_ltv: number;
  median_predicted_ltv: number;
  distribution: LtvBucket[];
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface AtRiskUser {
  user_id: number;
  churn_prob: number;
  recency_days: number;
  frequency: number;
  monetary: number;
  channel: string;
  city: string;
}

export interface ChurnResult {
  churn_recency_days: number;
  trained_users: number;
  churn_rate: number;
  auc: number;
  at_risk_count: number;
  feature_importance: FeatureImportance[];
  at_risk_top: AtRiskUser[];
}

/* ---------------- MMM ---------------- */

export interface MmmBaseline {
  contribution: number;
  share: number;
  avg_daily: number;
}

export interface MmmChannel {
  channel: string;
  spend: number;
  contribution: number;
  share: number;
  roas: number;
  marginal_roas: number;
  adstock_alpha: number;
  saturation_S: number;
  saturation_K: number;
}

export interface BudgetChannel {
  channel: string;
  current: number;
  suggested: number;
  delta_pct: number;
}

export interface BudgetPlan {
  total_budget: number;
  expected_gmv_current: number;
  expected_gmv_optimal: number;
  gain_pct: number;
  channels: BudgetChannel[];
}

export interface MmmResult {
  total_gmv: number;
  model_fit_r2: number;
  baseline: MmmBaseline;
  channels: MmmChannel[];
  budget_plan: BudgetPlan;
  parameters: {
    adstock: Record<string, number>;
    hill_S: Record<string, number>;
    hill_K: Record<string, number>;
  };
}

/* ---------------- 裂变增长 ---------------- */

export interface KFactorPoint {
  month: string;
  k_factor: number;
  inviters: number;
  invites_sent: number;
  accepted: number;
}

export interface TierRoi {
  tier: number;
  invites_sent: number;
  accepted: number;
  reward_cost: number;
  registered: number;
  first_order: number;
  gmv: number;
  roi: number;
}

export interface FunnelStep {
  step: string;
  users: number;
}

export interface FunnelConversion {
  from: string;
  to: string;
  rate: number;
}

export interface Funnel {
  steps: FunnelStep[];
  conversion: FunnelConversion[];
}

export interface TopInviter {
  inviter_id: number;
  invites_sent: number;
  accepted: number;
  registered: number;
  downstream_gmv: number;
}

export interface GrowthSummary {
  total_invites: number;
  total_accepted: number;
  k_factor_trend: KFactorPoint[];
  latest_k_factor: number;
  tier_roi: TierRoi[];
  funnel: Funnel;
  top_inviters: TopInviter[];
}

export interface InviteLink {
  source: number;
  target: number;
  tier: number;
  reward: number;
}

export interface GrowthTree {
  links: InviteLink[];
  count: number;
}

/* ---------------- AI 报告 ---------------- */

export interface ReportUserAgg {
  segments: UserSegments;
  ltv: { prediction: LtvPrediction };
  churn: ChurnResult;
}

export interface ReportContext {
  overview?: Overview;
  users?: ReportUserAgg;
  mmm?: MmmResult;
  growth?: GrowthSummary;
}
