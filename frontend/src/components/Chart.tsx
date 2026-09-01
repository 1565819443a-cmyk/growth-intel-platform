interface ChartProps {
  labels: string[];
  values: number[];
  className?: string;
  height?: string;
}

/** Lightweight accessible bar chart used by every configured dataset. */
export default function Chart({ labels, values, className = '', height = '320px' }: ChartProps) {
  const finite = values.map(value => Number.isFinite(value) ? value : 0);
  const max = Math.max(...finite, 1);
  return (
    <div className={`flex items-end gap-3 overflow-x-auto border-b border-l border-slate-200 px-4 pt-6 ${className}`} style={{ height }} role="img" aria-label="指标分组柱状图">
      {finite.map((value, index) => (
        <div className="flex h-full min-w-16 flex-1 flex-col items-center justify-end" key={`${labels[index]}-${index}`} title={`${labels[index]}: ${value.toLocaleString('zh-CN',{maximumFractionDigits:2})}`}>
          <span className="mb-2 text-xs font-semibold text-slate-600">{value.toLocaleString('zh-CN',{maximumFractionDigits:2})}</span>
          <div className="w-full rounded-t-lg bg-gradient-to-t from-cyan-500 to-indigo-400 transition-all" style={{ height:`${Math.max(3,82*value/max)}%` }} />
          <span className="mt-2 max-w-24 truncate text-xs text-slate-500">{labels[index]}</span>
        </div>
      ))}
    </div>
  );
}
