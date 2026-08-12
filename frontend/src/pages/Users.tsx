import { useMemo } from 'react';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import Chart from '../components/Chart';
import { Card, ErrorBox, PageHeader, Spinner } from '../components/UI';
import { fmtCompact, fmtMoney, fmtPct } from '../lib/format';

export default function Users() {
  const segments = useApi(api.segments);
  const cohort = useApi(api.cohort);
  const ltvPred = useApi(api.ltvPrediction);
  const churn = useApi(api.churn);

  const loading = segments.loading || cohort.loading || ltvPred.loading || churn.loading;
  const error = segments.error ?? cohort.error ?? ltvPred.error ?? churn.error;

  if (loading) return <Spinner text="加载用户分析…" />;
  if (error) return <ErrorBox message={error} />;
  if (!segments.data || !cohort.data || !ltvPred.data || !churn.data) return <ErrorBox message="无数据" />;

  return (
    <div>
      <PageHeader
        title="用户分层与生命周期"
        desc="RFM 分层 · 留存队列 · LTV 预测 · 流失预警"
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="用户分层（RFM）">
          <SegmentChart segments={segments.data.segments} />
        </Card>
        <Card title="分群画像">
          <SegmentTable segments={segments.data.segments} />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="留存率（注册周队列）">
          <RetentionChart data={cohort.data} />
        </Card>
        <Card title="累计 LTV（注册周队列）">
          <LtvChart data={cohort.data} />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="未来 90 天 LTV 预测分布">
          <LtvPredChart data={ltvPred.data} />
        </Card>
        <Card title="流失预警模型">
          <ChurnPanel data={churn.data} />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="高价值 / 高潜力 Top 用户" className="xl:col-span-2">
          <TopUsersTable top={segments.data.top_users} />
        </Card>
        <Card title="高流失风险用户（Top 10）">
          <AtRiskList users={churn.data.at_risk_top} />
        </Card>
      </div>
    </div>
  );
}

/* ---------------- 图表 ---------------- */

function SegmentChart({ segments }: { segments: { name: string; share: number; count: number }[] }) {
  const option = useMemo(() => {
    const palette: Record<string, string> = {
      高价值: '#f59e0b', 高潜力: '#4f46e5', 新客: '#06b6d4', 一般: '#94a3b8', 流失预警: '#f43f5e', 沉睡: '#cbd5e1',
    };
    const nonEmpty = segments.filter((s) => s.count > 0);
    return {
      tooltip: { trigger: 'item', formatter: '{b}<br/>占比 {d}%<br/>人数 {c}' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '45%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b}\n{d}%' },
          data: nonEmpty.map((s) => ({ name: s.name, value: s.count, itemStyle: { color: palette[s.name] ?? '#64748b' } })),
        },
      ],
    };
  }, [segments]);
  return <Chart option={option} height="300px" />;
}

function SegmentTable({ segments }: { segments: { name: string; count: number; share: number; gmv_share: number; avg_recency_days: number; avg_frequency: number; avg_monetary: number }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
            <th className="pb-2 font-medium">分群</th>
            <th className="pb-2 text-right font-medium">人数</th>
            <th className="pb-2 text-right font-medium">占比</th>
            <th className="pb-2 text-right font-medium">GMV占比</th>
            <th className="pb-2 text-right font-medium">客单</th>
            <th className="pb-2 text-right font-medium">频次</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((s) => (
            <tr key={s.name} className="border-b border-slate-50 last:border-0">
              <td className="py-2 font-medium text-slate-700">{s.name}</td>
              <td className="py-2 text-right tabular-nums">{fmtCompact(s.count)}</td>
              <td className="py-2 text-right tabular-nums">{fmtPct(s.share)}</td>
              <td className="py-2 text-right tabular-nums">{fmtPct(s.gmv_share)}</td>
              <td className="py-2 text-right tabular-nums">¥{fmtCompact(s.avg_monetary)}</td>
              <td className="py-2 text-right tabular-nums">{s.avg_frequency.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-slate-400">流失预警用户贡献 80%+ GMV，是需要重点干预的人群。</p>
    </div>
  );
}

function RetentionChart({ data }: { data: { weeks: number[]; retention: { cohort: string; rates: number[] }[] } }) {
  const option = useMemo(() => {
    const cohorts = data.retention;
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, type: 'scroll' },
      grid: { left: 8, right: 8, top: 34, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: data.weeks.map((w) => `W${w}`) },
      yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
      series: cohorts.map((c) => ({
        name: c.cohort,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.8 },
        data: c.rates,
      })),
    };
  }, [data]);
  return <Chart option={option} height="300px" />;
}

function LtvChart({ data }: { data: { weeks: number[]; ltv: { cohort: string; values: number[] }[] } }) {
  const option = useMemo(() => {
    const x = data.weeks.map((w) => `W${w}`);
    return {
      tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => `¥${fmtCompact(Number(v))}` },
      legend: { top: 0, type: 'scroll' },
      grid: { left: 8, right: 8, top: 34, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: x },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtCompact(v) } },
      series: data.ltv.map((c) => ({
        name: c.cohort,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.8 },
        data: c.values,
      })),
    };
  }, [data]);
  return <Chart option={option} height="300px" />;
}

function LtvPredChart({ data }: { data: { distribution: { bucket: string; count: number }[] } }) {
  const option = useMemo(() => {
    const dist = data.distribution;
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 8, right: 8, top: 16, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: dist.map((d) => d.bucket) },
      yAxis: { type: 'value' },
      series: [
        {
          type: 'bar',
          barWidth: 40,
          itemStyle: { color: '#6366f1', borderRadius: [6, 6, 0, 0] },
          data: dist.map((d) => d.count),
        },
      ],
    };
  }, [data]);
  return <Chart option={option} height="300px" />;
}

/* ---------------- 面板 ---------------- */

function ChurnPanel({ data }: { data: { churn_rate: number; auc: number; at_risk_count: number; trained_users: number; feature_importance: { feature: string; importance: number }[] } }) {
  const option = useMemo(() => {
    const fi = data.feature_importance.filter((f) => f.importance > 0).slice(0, 8);
    return {
      grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: 'value', max: 1 },
      yAxis: { type: 'category', data: fi.map((f) => f.feature).reverse() },
      series: [
        {
          type: 'bar',
          barWidth: 14,
          itemStyle: { color: '#f43f5e', borderRadius: [0, 4, 4, 0] },
          data: fi.map((f) => f.importance).reverse(),
        },
      ],
    };
  }, [data]);
  return (
    <div>
      <div className="mb-3 grid grid-cols-2 gap-3">
        <Metric label="模型流失率" value={fmtPct(data.churn_rate * 100, 1)} />
        <Metric label="AUC" value={data.auc.toFixed(3)} />
        <Metric label="风险用户数" value={fmtCompact(data.at_risk_count)} />
        <Metric label="训练样本" value={fmtCompact(data.trained_users)} />
      </div>
      <p className="mb-2 text-xs text-slate-500">特征重要性（梯度提升树）</p>
      <Chart option={option} height="200px" />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-0.5 text-lg font-semibold tabular-nums text-slate-800">{value}</div>
    </div>
  );
}

function TopUsersTable({ top }: { top: { user_id: number; rfm_class: string; recency_days: number; frequency: number; monetary: number }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
            <th className="pb-2 font-medium">用户ID</th>
            <th className="pb-2 font-medium">分群</th>
            <th className="pb-2 text-right font-medium">距上次活跃</th>
            <th className="pb-2 text-right font-medium">频次</th>
            <th className="pb-2 text-right font-medium">累计消费</th>
          </tr>
        </thead>
        <tbody>
          {top.slice(0, 10).map((u) => (
            <tr key={u.user_id} className="border-b border-slate-50 last:border-0">
              <td className="py-2 tabular-nums">#{u.user_id}</td>
              <td className="py-2">
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">{u.rfm_class}</span>
              </td>
              <td className="py-2 text-right tabular-nums">{u.recency_days}天</td>
              <td className="py-2 text-right tabular-nums">{u.frequency}单</td>
              <td className="py-2 text-right font-medium tabular-nums">¥{fmtMoney(u.monetary)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AtRiskList({ users }: { users: { user_id: number; churn_prob: number; recency_days: number; monetary: number; channel: string; city: string }[] }) {
  return (
    <div className="divide-y divide-slate-50">
      {users.slice(0, 10).map((u) => (
        <div key={u.user_id} className="flex items-center justify-between py-2">
          <div>
            <div className="text-sm font-medium tabular-nums text-slate-800">
              #{u.user_id}
              <span className="ml-2 rounded bg-rose-50 px-1.5 py-0.5 text-[11px] font-medium text-rose-600">
                流失概率 {(u.churn_prob * 100).toFixed(0)}%
              </span>
            </div>
            <div className="mt-0.5 text-xs text-slate-400">
              {u.city} · {u.channel} · 距上次 {u.recency_days} 天
            </div>
          </div>
          <div className="text-right text-xs text-slate-500">
            <div className="font-medium tabular-nums text-slate-700">¥{fmtCompact(u.monetary)}</div>
            <div>历史消费</div>
          </div>
        </div>
      ))}
    </div>
  );
}
