import { useMemo } from 'react';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import Chart from '../components/Chart';
import { Card, ErrorBox, PageHeader, Spinner } from '../components/UI';
import KpiCard from '../components/UI';
import { fmtCompact, fmtMoney, fmtPct } from '../lib/format';

export default function Growth() {
  const summary = useApi(api.growthSummary);
  const tree = useApi(api.growthTree);

  const loading = summary.loading || tree.loading;
  const error = summary.error ?? tree.error;
  if (loading) return <Spinner text="加载裂变数据…" />;
  if (error) return <ErrorBox message={error} />;
  if (!summary.data) return <ErrorBox message="无数据" />;

  const s = summary.data;
  return (
    <div>
      <PageHeader
        title="裂变增长归因"
        desc="邀请链路 · K 因子 · 激励阶梯 ROI · 转化漏斗"
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="累计邀请" value={fmtCompact(s.total_invites)} sub="分享链接发出数" />
        <KpiCard label="被接受邀请" value={fmtCompact(s.total_accepted)} sub="好友接受并注册" />
        <KpiCard
          label="最新 K 因子"
          value={s.latest_k_factor.toFixed(3)}
          sub="人均带来有效新客"
          accent={s.latest_k_factor < 1 ? 'text-amber-600' : 'text-emerald-600'}
        />
        <KpiCard label="邀请接受率" value={fmtPct((s.total_accepted / s.total_invites) * 100)} sub="整体链路质量" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="月度 K 因子趋势">
          <KFactorChart data={s.k_factor_trend} />
        </Card>
        <Card title="激励阶梯 ROI（每 1 元奖励带回 GMV）">
          <TierRoiChart data={s.tier_roi} />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="裂变漏斗（浏览 → 分享 → 注册 → 首单）">
          <FunnelChart data={s.funnel} />
        </Card>
        <Card title="Top 邀请人">
          <TopInvitersTable list={s.top_inviters} />
        </Card>
      </div>

      <div className="mt-6">
        <Card title="邀请关系网络（Top 邀请人 × 被邀请用户）" extra={<span className="text-xs text-slate-400">共 {tree.data?.count ?? 0} 条邀请关系 · 图布局</span>}>
          <InviteGraph links={tree.data?.links ?? []} />
        </Card>
      </div>
    </div>
  );
}

function KFactorChart({ data }: { data: { month: string; k_factor: number; invites_sent: number; accepted: number }[] }) {
  const option = useMemo(() => {
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['K 因子'], top: 0 },
      grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: data.map((d) => d.month) },
      yAxis: {
        type: 'value',
        name: 'K',
        axisLabel: { formatter: (v: number) => v.toFixed(1) },
        splitLine: { lineStyle: { type: 'dashed' } },
      },
      series: [
        {
          name: 'K 因子',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { width: 3, color: '#06b6d4' },
          itemStyle: { color: '#06b6d4' },
          areaStyle: { opacity: 0.1, color: '#06b6d4' },
          data: data.map((d) => d.k_factor),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#f43f5e', type: 'dashed' },
            label: { formatter: '健康线 1.0', position: 'insideEndTop' },
            data: [{ yAxis: 1 }],
          },
        },
      ],
    };
  }, [data]);
  return <Chart option={option} height="280px" />;
}

function TierRoiChart({ data }: { data: { tier: number; reward_cost: number; gmv: number; roi: number; invites_sent: number; accepted: number }[] }) {
  const option = useMemo(() => {
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['GMV', '奖励成本'], top: 0 },
      grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: data.map((d) => `满${d.tier}人档`) },
      yAxis: [
        { type: 'value', axisLabel: { formatter: (v: number) => fmtCompact(v) } },
        { type: 'value', name: 'ROI' },
      ],
      series: [
        {
          name: 'GMV',
          type: 'bar',
          barWidth: 26,
          itemStyle: { color: '#10b981', borderRadius: [6, 6, 0, 0] },
          data: data.map((d) => d.gmv),
        },
        {
          name: '奖励成本',
          type: 'bar',
          barWidth: 26,
          itemStyle: { color: '#fbbf24', borderRadius: [6, 6, 0, 0] },
          data: data.map((d) => d.reward_cost),
        },
        {
          name: 'ROI',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: { width: 2.5, color: '#8b5cf6' },
          itemStyle: { color: '#8b5cf6' },
          label: { show: true, position: 'top', formatter: (p: { value: number }) => p.value.toFixed(1) },
          data: data.map((d) => d.roi),
        },
      ],
    };
  }, [data]);
  return <Chart option={option} height="280px" />;
}

function FunnelChart({ data }: { data: { steps: { step: string; users: number }[]; conversion: { from: string; to: string; rate: number }[] } }) {
  const rows = data.steps.map((s, i) => {
    const prev = i > 0 ? data.steps[i - 1].users : null;
    const convRate = prev ? (s.users / prev) * 100 : 100;
    return { ...s, convRate };
  });
  return (
    <div>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <FunnelBar key={r.step} step={r.step} users={r.users} rate={r.convRate} color={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
        ))}
      </div>
      <div className="mt-4 space-y-1 text-xs text-slate-500">
        {data.conversion.map((c) => (
          <div key={`${c.from}-${c.to}`}>
            {c.from} → {c.to}：<span className="font-medium text-slate-700">{fmtPct(c.rate)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const FUNNEL_COLORS = ['#4f46e5', '#6366f1', '#818cf8', '#a5b4fc'];

function FunnelBar({ step, users, rate, color }: { step: string; users: number; rate: number; color: string }) {
  const width = Math.max(8, Math.min(100, rate));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="font-medium text-slate-600">{step}</span>
        <span className="tabular-nums text-slate-400">
          {fmtCompact(users)} 人{rate < 100 && ` · ${fmtPct(rate)}`}
        </span>
      </div>
      <div className="h-8 w-full overflow-hidden rounded-lg bg-slate-100">
        <div
          className="flex h-full items-center rounded-lg pl-2 text-xs font-medium text-white"
          style={{ width: `${width}%`, background: color, minWidth: 40 }}
        >
          {fmtCompact(users)}
        </div>
      </div>
    </div>
  );
}

function TopInvitersTable({ list }: { list: { inviter_id: number; invites_sent: number; accepted: number; registered: number; downstream_gmv: number }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
            <th className="pb-2 font-medium">邀请人</th>
            <th className="pb-2 text-right font-medium">发出邀请</th>
            <th className="pb-2 text-right font-medium">接受</th>
            <th className="pb-2 text-right font-medium">成功注册</th>
            <th className="pb-2 text-right font-medium">下游 GMV</th>
          </tr>
        </thead>
        <tbody>
          {list.slice(0, 12).map((u) => (
            <tr key={u.inviter_id} className="border-b border-slate-50 last:border-0">
              <td className="py-2 tabular-nums font-medium text-slate-700">#{u.inviter_id}</td>
              <td className="py-2 text-right tabular-nums">{u.invites_sent}</td>
              <td className="py-2 text-right tabular-nums">{u.accepted}</td>
              <td className="py-2 text-right tabular-nums">{u.registered}</td>
              <td className="py-2 text-right font-medium tabular-nums">¥{fmtMoney(u.downstream_gmv)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InviteGraph({ links }: { links: { source: number; target: number; tier: number; reward: number }[] }) {
  const option = useMemo(() => {
    const sources = new Set(links.map((l) => l.source));
    const targets = new Set(links.map((l) => l.target));
    const ids = new Set([...sources, ...targets]);
    const nodes = Array.from(ids).map((id) => ({
      id: String(id),
      name: String(id),
      symbolSize: sources.has(id) ? 26 : 10,
      itemStyle: { color: sources.has(id) ? '#4f46e5' : '#94a3b8' },
      label: { show: sources.has(id) },
    }));
    return {
      tooltip: {
        formatter: (p: { dataType: string; data: { name: string } }) => `用户 #${p.data.name}`,
      },
      animationDurationUpdate: 1200,
      animationEasingUpdate: 'quinticInOut' as const,
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          force: { repulsion: 90, edgeLength: 60, gravity: 0.1 },
          data: nodes,
          links: links.map((l) => ({
            source: String(l.source),
            target: String(l.target),
            lineStyle: { color: TIER_COLOR[l.tier] ?? '#cbd5e1', width: 1.5, opacity: 0.7 },
          })),
          label: { position: 'bottom', fontSize: 10, color: '#64748b' },
          lineStyle: { curveness: 0.15 },
        },
      ],
    };
  }, [links]);
  return (
    <div>
      <Chart option={option} height="360px" />
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
        {[3, 5, 10].map((t) => (
          <span key={t} className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-6 rounded" style={{ background: TIER_COLOR[t] }} />
            满 {t} 人档（¥{t === 3 ? 20 : t === 5 ? 40 : 100} 奖励）
          </span>
        ))}
      </div>
    </div>
  );
}

const TIER_COLOR: Record<number, string> = { 3: '#10b981', 5: '#f59e0b', 10: '#f43f5e' };
