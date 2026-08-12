/* 统一 API 封装：GET + SSE 流式 */

import type {
  ChurnResult,
  Cohort,
  GrowthSummary,
  GrowthTree,
  LtvPrediction,
  MmmResult,
  Overview,
  ReportContext,
  UserSegments,
} from '../types';

// API 基址：生产用 VITE_API_BASE 指向 Render 后端（如 https://growth-intel-api.onrender.com），
// 开发环境走 Vite 代理（/api → localhost:8000）。
const BASE = import.meta.env.VITE_API_BASE || '/api';

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} 失败: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export const api = {
  overview: () => getJson<Overview>('/overview'),
  segments: () => getJson<UserSegments>('/users/segments'),
  cohort: () => getJson<Cohort>('/users/ltv/cohort'),
  ltvPrediction: () => getJson<LtvPrediction>('/users/ltv/prediction'),
  churn: () => getJson<ChurnResult>('/users/churn'),
  mmm: () => getJson<MmmResult>('/mmm/result'),
  growthSummary: () => getJson<GrowthSummary>('/growth/summary'),
  growthTree: () => getJson<GrowthTree>('/growth/tree'),
};

/** SSE 流式生成报告：逐 chunk 回调已解析的 {delta} 文本。 */
export async function streamReport(
  ctx: ReportContext,
  onChunk: (delta: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ctx),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`POST /report 失败: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // 按 SSE 块解析，兼容块跨 chunk 边界
    let sep = buffer.indexOf('\n\n');
    while (sep >= 0) {
      const block = buffer.slice(0, sep).trim();
      buffer = buffer.slice(sep + 2);
      if (block.startsWith('data:')) {
        const payload = block.replace(/^data:\s*/, '');
        try {
          const parsed = JSON.parse(payload) as { delta?: string; done?: boolean };
          if (parsed.delta) onChunk(parsed.delta);
          if (parsed.done) return;
        } catch {
          // 忽略非 JSON 或断行片段
        }
      }
      sep = buffer.indexOf('\n\n');
    }
  }
}
