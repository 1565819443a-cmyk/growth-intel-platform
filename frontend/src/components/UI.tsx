import type { ReactNode } from 'react';

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
  hint?: string;
}

export default function KpiCard({ label, value, sub, accent = 'text-slate-900', hint }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className={`mt-2 text-2xl font-semibold tabular-nums ${accent}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
      {hint && <div className="mt-1 text-xs font-medium text-emerald-600">{hint}</div>}
    </div>
  );
}

export function Card({ title, extra, children, className = '' }: {
  title?: string;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || extra) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="text-sm font-semibold text-slate-700">{title}</h3>}
          {extra}
        </div>
      )}
      {children}
    </div>
  );
}

export function PageHeader({ title, desc, extra }: {
  title: string;
  desc?: string;
  extra?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {desc && <p className="mt-1 text-sm text-slate-500">{desc}</p>}
      </div>
      {extra}
    </div>
  );
}

export function Spinner({ text = '加载中…' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
      <div className="mt-3 text-sm">{text}</div>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-600">
      加载失败：{message}
    </div>
  );
}
