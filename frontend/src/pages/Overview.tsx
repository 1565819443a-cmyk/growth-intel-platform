import { useMemo } from 'react';
import { api } from '../api/client';
import { useApi } from '../api/useApi';
import Chart from '../components/Chart';
import { Card, ErrorBox, PageHeader, Spinner } from '../components/UI';
import KpiCard from '../components/UI';
import { channelColor, channelLabel, fmtCompact, fmtDeltaPct, fmtMoney } from '../lib/format';

export default function Overview() {
  const { data, loading, error } = useApi(api.overview);

  const trendOption = useMemo(() => {
    if (!data) return {};
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['GMV', '订单量'], top: 0 },
      grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: data.trend.map((d) => d.date), boundaryGap: false },
      yAxis: [
        { type: 'value', name: 'GMV(¥)', axisLabel: { formatter: (v: number) => fmtCompact(v) } },
        { type: 'value', name: '订单', splitLine: { show: false } },
      ],
      series: [
        {
          name: 'GMV',
          type: 'line',
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2.5, color: '#4f46e5' },
          itemStyle: { color: '#4f46e5' },
          areaStyle: { opacity: 0.08, color: '#4f46e5' },
          data: data.trend.map((d) => d.gmv),
        },
        {
          name: '订单量',
          type: 'line',
          smooth: true,
          showSymbol: false,
          yAxisIndex: 1,
          lineStyle: { width: 2, color: '#f59e0b' },
          itemStyle: { color: '#f59e0b' },
          data: data.trend.map((d) => d.orders),
        },
      ],
    };
  }, [data]);

  if (loading) return <Spinner text="加载总览数据…" />;
  if (error || !data) return <ErrorBox message={error ?? '无数据'} />;
  const { period, summary, channels, trend } = data;
  const periodLabel = `${period.start} ~ ${period.end}`;

  return (
    <div>
      <PageHeader
        title="经营总览"
        desc={`数据区间 ${periodLabel} · ${trend.length} 天`}
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        <KpiCard label="GMV" value={`¥${fmtMoney(summary.total_gmv)}`} sub="区间总成交额" />
        <KpiCard label="订单量" value={fmtCompact(summary.total_orders)} sub="付费订单总数" />
        <KpiCard label="累计注册" value={fmtCompact(summary.total_users)} sub="新客 + 存量" />
        <KpiCard label="MAU" value={fmtCompact(summary.mau)} sub="近 30 天活跃用户" />
        <KpiCard label="客单价 AOV" value={`¥${summary.aov.toFixed(2)}`} sub="GMV / 订单" />
        <KpiCard label="投放花费" value={`¥${fmtMoney(summary.total_spend)}`} sub="全渠道广告支出" />
        <KpiCard
          label="ROAS"
          value={summary.roas.toFixed(3)}
          sub="整体投入产出比"
          accent={summary.roas >= 1.5 ? 'text-emerald-600' : 'text-slate-900'}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="GMV 与订单量趋势" className="xl:col-span-2">
          <Chart option={trendOption} height="340px" />
        </Card>

        <Card title="渠道投放效率">
          <div className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs text-slate-400">
                  <th className="pb-2 font-medium">渠道</th>
                  <th className="pb-2 text-right font-medium">花费</th>
                  <th className="pb-2 text-right font-medium">GMV</th>
                  <th className="pb-2 text-right font-medium">ROAS</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((c) => (
                  <tr key={c.channel} className="border-b border-slate-50 last:border-0">
                    <td className="py-2.5">
                      <span className="inline-flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: channelColor(c.channel) }} />
                        {channelLabel(c.channel)}
                      </span>
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-slate-600">¥{fmtCompact(c.spend)}</td>
                    <td className="py-2.5 text-right tabular-nums text-slate-600">¥{fmtCompact(c.gmv)}</td>
                    <td className="py-2.5 text-right font-medium tabular-nums">
                      {c.channel === 'organic' ? '—' : c.roas.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            裂变邀请渠道 ROAS {channels.find((c) => c.channel === 'invite')?.roas.toFixed(2) ?? '—'}，显著高于信息流广告——预算错配的信号。
          </p>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="渠道花费结构" className="xl:col-span-2">
          <ChannelSpendChart channels={channels} />
        </Card>
        <Card title="近期核心指标">
          <div className="space-y-4">
            <MiniTrend label="DAU（活跃用户）" data={trend.slice(-30).map((d) => d.active_users)} color="#4f46e5" />
            <MiniTrend label="日新增注册" data={trend.slice(-30).map((d) => d.new_users)} color="#06b6d4" />
            <MiniTrend label="日 ROAS" data={trend.slice(-30).map((d) => d.roas)} color="#f59e0b" />
          </div>
        </Card>
      </div>
    </div>
  );
}

function ChannelSpendChart({ channels }: { channels: { channel: string; spend: number; gmv: number }[] }) {
  const option = useMemo(() => {
    const paid = channels.filter((c) => c.channel !== 'organic');
    const cats = paid.map((c) => channelLabel(c.channel));
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['花费', 'GMV'], top: 0 },
      grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: cats },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmtCompact(v) } },
      series: [
        {
          name: '花费',
          type: 'bar',
          barWidth: 22,
          itemStyle: { color: '#cbd5e1', borderRadius: [6, 6, 0, 0] },
          data: paid.map((c) => c.spend),
        },
        {
          name: 'GMV',
          type: 'bar',
          barWidth: 22,
          itemStyle: { color: '#6366f1', borderRadius: [6, 6, 0, 0] },
          data: paid.map((c) => c.gmv),
        },
      ],
    };
  }, [channels]);
  return <Chart option={option} height="300px" />;
}

function MiniTrend({ label, data, color }: { label: string; data: number[]; color: string }) {
  const option = useMemo(
    () => ({
      grid: { left: 4, right: 4, top: 8, bottom: 0 },
      xAxis: { type: 'category', show: false, data: data.map((_, i) => i) },
      yAxis: { type: 'value', show: false },
      series: [
        {
          type: 'line',
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2, color },
          areaStyle: { opacity: 0.12, color },
          data,
        },
      ],
    }),
    [data, color],
  );
  const last = data[data.length - 1];
  const prev = data.length > 1 ? data[data.length - 2] : last;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-slate-800">
          {fmtCompact(Math.round(last))}
          <span className="ml-2 text-xs font-normal text-slate-400">
            {last >= prev ? '↗' : '↘'} {fmtDeltaPct(((last - prev) / Math.max(prev, 0.0001)) * 100)}
          </span>
        </span>
      </div>
      <Chart option={option} height="56px" />
    </div>
  );
}
