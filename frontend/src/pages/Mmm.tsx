import { useMemo } from 'react';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import Chart from '../components/Chart';
import { Card, ErrorBox, PageHeader, Spinner } from '../components/UI';
import KpiCard from '../components/UI';
import { channelColor, channelLabel, fmtCompact, fmtDeltaPct, fmtMoney, fmtPct } from '../lib/format';

export default function Mmm() {
  const { data, loading, error } = useApi(api.mmm);
  const channels = data?.channels ?? [];
  const plan = data?.budget_plan;

  const contribOption = useMemo(() => {
    if (!data) return {};
    const items = [...channels.map((c) => ({ name: channelLabel(c.channel), value: c.contribution }))];
    return {
      tooltip: { trigger: 'item', formatter: '{b}<br/>贡献 ¥{c}<br/>{d}%' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['40%', '68%'],
          center: ['50%', '44%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b}\n{d}%' },
          data: items.map((it) => ({
            ...it,
            itemStyle: { color: channelColor(it.name) },
          })),
        },
      ],
    };
  }, [data, channels]);

  const roasOption = useMemo(() => {
    if (!channels.length) return {};
    const cats = channels.map((c) => channelLabel(c.channel));
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['ROAS', '边际 ROAS'], top: 0 },
      grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: cats },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'ROAS',
          type: 'bar',
          barWidth: 20,
          itemStyle: { color: '#6366f1', borderRadius: [6, 6, 0, 0] },
          data: channels.map((c) => c.roas),
        },
        {
          name: '边际 ROAS',
          type: 'bar',
          barWidth: 20,
          itemStyle: { color: '#f59e0b', borderRadius: [6, 6, 0, 0] },
          data: channels.map((c) => c.marginal_roas),
        },
      ],
    };
  }, [channels]);

  const spendShare = useMemo(() => {
    if (!channels.length) return {};
    const total = channels.reduce((s, c) => s + c.spend, 0);
    const cats = channels.map((c) => channelLabel(c.channel));
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 8, right: 40, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: cats },
      yAxis: {
        type: 'value',
        max: 50,
        axisLabel: { formatter: '{value}%' },
        name: '花费占比',
      },
      series: [
        {
          name: '花费占比',
          type: 'bar',
          barWidth: 30,
          itemStyle: { color: '#e2e8f0', borderRadius: [6, 6, 0, 0] },
          label: { show: true, position: 'top', formatter: (p: { value: number }) => `${p.value.toFixed(1)}%` },
          data: channels.map((c) => (c.spend / total) * 100),
        },
      ],
    };
  }, [channels]);

  if (loading) return <Spinner text="拟合营销组合模型…" />;
  if (error || !data) return <ErrorBox message={error ?? '无数据'} />;

  return (
    <div>
      <PageHeader
        title="MMM 营销组合模型"
        desc="几何 adstock + Hill 饱和 · 坐标下降网格拟合 · 固定预算下的最优重分配"
        extra={
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
            R² = {data.model_fit_r2.toFixed(3)}
          </span>
        }
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="区间 GMV" value={`¥${fmtMoney(data.total_gmv)}`} sub="模型拟合对象" />
        <KpiCard label="自然增长基线占比" value={fmtPct(data.baseline.share)} sub="非媒体贡献" />
        <KpiCard label="媒体贡献占比" value={fmtPct(100 - data.baseline.share)} sub="四渠道合计" />
        <KpiCard
          label="重分配可提升"
          value={`+${plan?.gain_pct.toFixed(1) ?? '—'}%`}
          sub="预算重分配后的预期 GMV 增量"
          accent="text-emerald-600"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="渠道贡献分解">
          <Chart option={contribOption} height="320px" />
        </Card>
        <Card title="ROAS 与边际 ROAS">
          <Chart option={roasOption} height="320px" />
        </Card>
        <Card title="花费结构（现状）">
          <Chart option={spendShare} height="320px" />
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title="预算重分配方案">
          {plan && <BudgetPlan plan={plan} channels={channels} />}
        </Card>
        <Card title="模型参数">
          {data.parameters && <ParamsTable channels={channels} />}
        </Card>
      </div>
    </div>
  );
}

function BudgetPlan({ plan, channels }: { plan: { expected_gmv_current: number; expected_gmv_optimal: number; gain_pct: number; channels: { channel: string; current: number; suggested: number; delta_pct: number }[] }; channels: { channel: string; marginal_roas: number }[] }) {
  const option = useMemo(() => {
    const cats = plan.channels.map((c) => channelLabel(c.channel));
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['当前预算', '建议预算'], top: 0 },
      grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: cats },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtCompact(v) } },
      series: [
        {
          name: '当前预算',
          type: 'bar',
          barWidth: 20,
          itemStyle: { color: '#94a3b8', borderRadius: [6, 6, 0, 0] },
          data: plan.channels.map((c) => c.current),
        },
        {
          name: '建议预算',
          type: 'bar',
          barWidth: 20,
          itemStyle: { color: '#10b981', borderRadius: [6, 6, 0, 0] },
          data: plan.channels.map((c) => c.suggested),
        },
      ],
    };
  }, [plan]);

  return (
    <div>
      <div className="mb-4 grid grid-cols-3 gap-3">
        <Metric label="当前预算 GMV" value={`¥${fmtMoney(plan.expected_gmv_current)}`} />
        <Metric label="重分配后 GMV" value={`¥${fmtMoney(plan.expected_gmv_optimal)}`} accent="text-emerald-600" />
        <Metric label="增量" value={fmtDeltaPct(plan.gain_pct)} accent="text-emerald-600" />
      </div>
      <Chart option={option} height="240px" />
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
              <th className="pb-2 font-medium">渠道</th>
              <th className="pb-2 text-right font-medium">当前</th>
              <th className="pb-2 text-right font-medium">建议</th>
              <th className="pb-2 text-right font-medium">调整</th>
            </tr>
          </thead>
          <tbody>
            {plan.channels.map((c) => (
              <tr key={c.channel} className="border-b border-slate-50 last:border-0">
                <td className="py-2 font-medium text-slate-700">{channelLabel(c.channel)}</td>
                <td className="py-2 text-right tabular-nums">¥{fmtCompact(c.current)}</td>
                <td className="py-2 text-right font-medium tabular-nums">¥{fmtCompact(c.suggested)}</td>
                <td className={`py-2 text-right font-semibold tabular-nums ${c.delta_pct >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                  {fmtDeltaPct(c.delta_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
        <b>故事</b>：信息流广告（ads）花了总预算的 <b>47%</b>，但边际 ROAS 最低（{channels.find((c) => c.channel === 'ads')?.marginal_roas.toFixed(3)}），已进入高度饱和区；
        裂变邀请（invite）仅占 5% 预算，边际 ROAS 却最高（{channels.find((c) => c.channel === 'invite')?.marginal_roas.toFixed(3)}）。
        把预算从低效渠道挪向高边际渠道（ads −20%、search −16%、social +50%、invite +50%），GMV 可提升 <b>{fmtDeltaPct(plan.gain_pct)}</b>。
      </p>
    </div>
  );
}

function Metric({ label, value, accent = 'text-slate-900' }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`mt-0.5 text-lg font-semibold tabular-nums ${accent}`}>{value}</div>
    </div>
  );
}

function ParamsTable({ channels }: {
  channels: { channel: string; adstock_alpha: number; saturation_S: number; saturation_K: number; marginal_roas: number }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
            <th className="pb-2 font-medium">渠道</th>
            <th className="pb-2 text-right font-medium">adstock α</th>
            <th className="pb-2 text-right font-medium">Hill S</th>
            <th className="pb-2 text-right font-medium">饱和 K</th>
            <th className="pb-2 text-right font-medium">边际ROAS</th>
          </tr>
        </thead>
        <tbody>
          {channels.map((c) => (
            <tr key={c.channel} className="border-b border-slate-50 last:border-0">
              <td className="py-2">
                <span className="inline-flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: channelColor(c.channel) }} />
                  {channelLabel(c.channel)}
                </span>
              </td>
              <td className="py-2 text-right tabular-nums">{c.adstock_alpha.toFixed(3)}</td>
              <td className="py-2 text-right tabular-nums">{c.saturation_S.toFixed(1)}</td>
              <td className="py-2 text-right tabular-nums">{fmtCompact(c.saturation_K)}</td>
              <td className="py-2 text-right font-medium tabular-nums">{c.marginal_roas.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-slate-400">
        adstock α 衡量投放的滞后效应（越大影响越持久）；Hill K 越小饱和越早、增量回报衰减越快。
        广告渠道 K 最大（{channels.find((c) => c.channel === 'ads')?.saturation_K.toLocaleString('zh-CN')}），对应高饱和。
      </p>
    </div>
  );
}
