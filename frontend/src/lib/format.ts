/* 数值格式化工具 */

export function fmtMoney(v: number, digits = 0): string {
  if (!Number.isFinite(v)) return '—';
  if (Math.abs(v) >= 1_0000_0000) return `${(v / 1_0000_0000).toFixed(digits)}亿`;
  if (Math.abs(v) >= 1_0000) return `${(v / 1_0000).toFixed(digits)}万`;
  return v.toLocaleString('zh-CN', { maximumFractionDigits: digits });
}

export function fmtCompact(v: number): string {
  if (!Number.isFinite(v)) return '—';
  return v.toLocaleString('zh-CN');
}

export function fmtPct(v: number, digits = 1): string {
  if (!Number.isFinite(v)) return '—';
  return `${v.toFixed(digits)}%`;
}

export function fmtDeltaPct(v: number): string {
  if (!Number.isFinite(v)) return '—';
  const s = v > 0 ? '+' : '';
  return `${s}${v.toFixed(1)}%`;
}

/** 渠道中文名 */
export const CHANNEL_LABEL: Record<string, string> = {
  search: '搜索广告',
  ads: '信息流广告',
  social: '社媒投放',
  invite: '裂变邀请',
  organic: '自然流量',
};

export function channelLabel(ch: string): string {
  return CHANNEL_LABEL[ch] ?? ch;
}

export const CHANNEL_COLOR: Record<string, string> = {
  search: '#3b82f6',
  ads: '#8b5cf6',
  social: '#06b6d4',
  invite: '#f59e0b',
  organic: '#94a3b8',
};

export function channelColor(ch: string): string {
  return CHANNEL_COLOR[ch] ?? '#64748b';
}

export const CHANNEL_ORDER = ['ads', 'search', 'social', 'invite', 'organic'];
