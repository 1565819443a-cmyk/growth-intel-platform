import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api, streamReport } from '../api/client';
import { Card, ErrorBox, PageHeader } from '../components/UI';
import { useApi } from '../api/useApi';
import type { ReportContext } from '../types';

export default function Report() {
  const overview = useApi(api.overview);
  const segments = useApi(api.segments);
  const ltvPred = useApi(api.ltvPrediction);
  const churn = useApi(api.churn);
  const mmm = useApi(api.mmm);
  const growth = useApi(api.growthSummary);

  const ready = overview.data && segments.data && ltvPred.data && churn.data && mmm.data && growth.data;
  const [status, setStatus] = useState<'idle' | 'streaming' | 'done'>('idle');
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const viewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = viewRef.current;
    if (el && status === 'streaming') el.scrollTop = el.scrollHeight;
  }, [text, status]);

  const ctx: ReportContext | null = useMemo(() => {
    if (!ready) return null;
    return {
      overview: overview.data!,
      users: {
        segments: segments.data!,
        ltv: { prediction: ltvPred.data! },
        churn: churn.data!,
      },
      mmm: mmm.data!,
      growth: growth.data!,
    };
  }, [ready, overview.data, segments.data, ltvPred.data, churn.data, mmm.data, growth.data]);

  const generate = async () => {
    if (!ctx) return;
    setText('');
    setError(null);
    setStatus('streaming');
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamReport(ctx, (delta) => setText((prev) => prev + delta), controller.signal);
      setStatus('done');
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setError(e instanceof Error ? e.message : String(e));
        setStatus('done');
      }
    }
  };

  const stop = () => abortRef.current?.abort();

  const loadingAll = overview.loading || segments.loading || ltvPred.loading || churn.loading || mmm.loading || growth.loading;
  const ctxError = overview.error ?? segments.error ?? ltvPred.error ?? churn.error ?? mmm.error ?? growth.error;

  return (
    <div>
      <PageHeader
        title="AI 策略报告"
        desc="基于总览、用户分层、MMM 与裂变数据，流式生成结构化经营策略报告"
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card title="报告生成" className="xl:col-span-1 h-fit">
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-2">
              <StatusDot ok={!!overview.data} loading={overview.loading} />
              <div>
                <div className="font-medium text-slate-700">经营总览</div>
                <div className="text-xs text-slate-400">KPI、渠道效率、趋势</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <StatusDot ok={!!segments.data} loading={segments.loading} />
              <div>
                <div className="font-medium text-slate-700">用户分层与生命周期</div>
                <div className="text-xs text-slate-400">RFM / LTV / 流失预警</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <StatusDot ok={!!mmm.data} loading={mmm.loading} />
              <div>
                <div className="font-medium text-slate-700">MMM 营销组合</div>
                <div className="text-xs text-slate-400">渠道贡献 / 预算重分配</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <StatusDot ok={!!growth.data} loading={growth.loading} />
              <div>
                <div className="font-medium text-slate-700">裂变增长</div>
                <div className="text-xs text-slate-400">K 因子 / 阶梯 ROI</div>
              </div>
            </div>

            {ctxError && <div className="text-xs text-rose-500">数据加载失败：{ctxError}</div>}

            <div className="pt-2">
              {status === 'streaming' ? (
                <button
                  onClick={stop}
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  停止生成
                </button>
              ) : (
                <button
                  onClick={generate}
                  disabled={!ready || loadingAll}
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {loadingAll ? '加载数据中…' : status === 'done' ? '重新生成报告' : '生成策略报告'}
                </button>
              )}
            </div>
            <p className="text-xs text-slate-400">
              报告调用 DeepSeek 流式生成；未配置 API Key 时使用本地模板兜底，保证演示可用。
            </p>
          </div>
        </Card>

        <Card
          title="报告内容"
          className="xl:col-span-2"
          extra={
            status === 'streaming' ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600">
                <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
                生成中…
              </span>
            ) : status === 'done' ? (
              <span className="text-xs text-emerald-600">已完成</span>
            ) : null
          }
        >
          {status === 'idle' ? (
            <div className="flex h-96 flex-col items-center justify-center text-center text-slate-400">
              <div className="mb-3 text-5xl">📊</div>
              <div className="text-sm">点击「生成策略报告」，将四类分析结果交给 LLM 归纳结论与可执行建议</div>
            </div>
          ) : (
            <div
              ref={viewRef}
              className="prose prose-sm max-w-none overflow-y-auto pr-2 text-sm leading-relaxed text-slate-700"
              style={{ maxHeight: 560 }}
            >
              {text ? <ReportMarkdown text={text} /> : <div className="text-slate-400">正在组织内容…</div>}
            </div>
          )}
          {error && status === 'done' && <ErrorBox message={error} />}
        </Card>
      </div>
    </div>
  );
}

function StatusDot({ ok, loading }: { ok: boolean; loading: boolean }) {
  if (loading) return <span className="mt-1 h-2.5 w-2.5 animate-pulse rounded-full bg-slate-300" />;
  return (
    <span className={`mt-1 h-2.5 w-2.5 rounded-full ${ok ? 'bg-emerald-500' : 'bg-rose-400'}`} />
  );
}

/** 极简 markdown 渲染：标题 / 列表 / 加粗 / 分隔线 / 段落。 */
function ReportMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  const nodes: ReactNode[] = [];
  let list: string[] = [];
  let key = 0;

  const flushList = () => {
    if (list.length) {
      nodes.push(
        <ul key={key++} className="my-2 list-disc pl-5">
          {list.map((li, i) => (
            <li key={i} className="my-0.5">{renderInline(li)}</li>
          ))}
        </ul>,
      );
      list = [];
    }
  };

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    if (line.trim() === '') {
      flushList();
      continue;
    }
    if (line.startsWith('---')) {
      flushList();
      nodes.push(<hr key={key++} className="my-3 border-slate-200" />);
      continue;
    }
    if (line.startsWith('### ')) {
      flushList();
      nodes.push(<h3 key={key++} className="mt-4 text-base font-semibold text-slate-800">{renderInline(line.slice(4))}</h3>);
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      nodes.push(<h2 key={key++} className="mt-5 text-lg font-bold text-slate-900">{renderInline(line.slice(3))}</h2>);
      continue;
    }
    if (line.startsWith('# ')) {
      flushList();
      nodes.push(<h1 key={key++} className="mt-5 text-xl font-bold text-slate-900">{renderInline(line.slice(2))}</h1>);
      continue;
    }
    const liMatch = line.match(/^\s*[-*]\s+(.+)$/);
    if (liMatch) {
      list.push(liMatch[1]);
      continue;
    }
    const numMatch = line.match(/^\s*\d+[.、]\s+(.+)$/);
    if (numMatch) {
      flushList();
      nodes.push(
        <p key={key++} className="my-1">
          <span className="font-semibold text-slate-700">· </span>
          {renderInline(numMatch[1])}
        </p>,
      );
      continue;
    }
    flushList();
    nodes.push(<p key={key++} className="my-1.5">{renderInline(line)}</p>);
  }
  flushList();
  return <>{nodes}</>;
}

function renderInline(s: string) {
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i} className="font-semibold text-slate-900">{p.slice(2, -2)}</strong>;
    }
    return <span key={i}>{p}</span>;
  });
}
