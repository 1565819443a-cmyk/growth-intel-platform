"""DeepSeek 策略报告：组装业务上下文 → prompt → 流式生成。

无 DEEPSEEK_API_KEY 时回退到本地模板报告（同样流式输出，保证演示可用）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterator, Optional

from openai import OpenAI

from ..config import settings


# --------------------------------------------------------------------------
# Prompt 组装
# --------------------------------------------------------------------------
def build_prompt(ctx: Dict[str, Any]) -> str:
    """把前端传入的分析结果 JSON 组装成结构化业务 prompt。"""
    o = ctx.get("overview", {})
    users = ctx.get("users", {})
    mmm = ctx.get("mmm", {})
    growth = ctx.get("growth", {})

    lines = [
        "你是一位资深跨境电商增长数据分析师。请基于下面的平台经营数据，输出一份结构化的中文经营策略报告。",
        "要求：用**## 标题 + 有序列表/短段落**组织；数字必须与给出的数据一致，不要编造；",
        "结论要直接、可执行，突出「哪些动作能带来最多 GMV 增量」。报告控制在 500 字以内。",
        "",
        "【一、总览】",
    ]

    sm = o.get("summary", {})
    lines.append(
        f"- 观察期：{o.get('period', {}).get('start', '-')} ~ {o.get('period', {}).get('end', '-')}；"
        f"总 GMV {sm.get('total_gmv', '-')} 元，订单 {sm.get('total_orders', '-')} 单，客单价 {sm.get('aov', '-')} 元"
    )
    lines.append(
        f"- 总用户 {sm.get('total_users', '-')}，MAU {sm.get('mau', '-')}；"
        f"总投放花费 {sm.get('total_spend', '-')} 元，整体 ROAS {sm.get('roas', '-')}"
    )
    chs = o.get("channels", [])
    if chs:
        top_ch = chs[0]
        lines.append(
            f"- 渠道 ROI：{top_ch.get('channel')} 贡献 GMV {top_ch.get('gmv', '-')}"
            f"（ROAS {top_ch.get('roas', '-')}），为当前最高效渠道"
        )

    lines.append("")
    lines.append("【二、用户分层与生命周期】")
    seg_resp = users.get("segments", {})
    segs = seg_resp.get("segments", []) if isinstance(seg_resp, dict) else seg_resp
    if segs:
        for s in segs[:4]:
            lines.append(
                f"- {s.get('name')}：{s.get('count')} 人（占 {s.get('share', '-')}%），"
                f"人均 GMV {s.get('avg_monetary', '-')} 元"
            )
    ltv = users.get("ltv", {}).get("prediction", {})
    if ltv:
        lines.append(
            f"- LTV 预测：平均未来 {ltv.get('horizon_days', 90)} 天 LTV "
            f"{ltv.get('avg_predicted_ltv', '-')} 元，中位数 {ltv.get('median_predicted_ltv', '-')} 元"
        )
    churn = users.get("churn", {})
    if churn:
        lines.append(
            f"- 流失预警：{churn.get('at_risk_count', '-')} 名用户处于流失风险"
            f"（模型 AUC {churn.get('auc', '-')}，主要特征 {churn.get('feature_importance', [{}])[0].get('feature', '-')}）"
        )

    lines.append("")
    lines.append("【三、营销组合模型 MMM】")
    if mmm.get("error"):
        lines.append(f"- {mmm.get('error')}")
    else:
        lines.append(f"- 模型拟合 R² = {mmm.get('model_fit_r2', '-')}")
        base = mmm.get("baseline", {})
        lines.append(f"- 自然增长基线贡献占比 {base.get('share', '-')}%")
        for c in mmm.get("channels", []):
            lines.append(
                f"- {c.get('channel')}：花费 {c.get('spend', '-')}，贡献占比 {c.get('share', '-')}%，"
                f"ROAS {c.get('roas', '-')}，边际 ROAS {c.get('marginal_roas', '-')}"
            )
        bp = mmm.get("budget_plan", {})
        if bp:
            lines.append(
                f"- 预算重分配建议：保持总预算，预计 GMV 提升 {bp.get('gain_pct', '-')}%"
            )

    lines.append("")
    lines.append("【四、裂变增长】")
    if growth.get("error"):
        lines.append(f"- {growth.get('error')}")
    else:
        lines.append(
            f"- 总邀请 {growth.get('total_invites', '-')}，接受 {growth.get('total_accepted', '-')}；"
            f"最新月 K 因子 {growth.get('latest_k_factor', '-')}"
        )
        for t in growth.get("tier_roi", []):
            lines.append(
                f"- 邀请 {t.get('tier')} 人档：奖励成本 {t.get('reward_cost', '-')} 元，"
                f"带来 {t.get('registered', '-')} 名注册、{t.get('first_order', '-')} 名首单，ROI {t.get('roi', '-')}"
            )

    lines.append("")
    lines.append("【五、可执行策略建议】请给出 3~5 条，按预期 GMV 增量排序，每条注明投放/运营动作与量化预期。")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# DeepSeek 流式
# --------------------------------------------------------------------------
def stream_report(ctx: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """返回 JSON 块的迭代器：{"delta": str} 文本增量；最后 {"done": true}。"""
    prompt = build_prompt(ctx)

    if not settings.deepseek_api_key:
        yield from _local_report(prompt, ctx)
        return

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": "你是资深跨境电商增长数据分析师，输出简洁可执行的中文报告。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            stream=True,
            max_tokens=1500,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"delta": chunk.choices[0].delta.content}
    except Exception as e:  # noqa: BLE001  Key 失效等异常 → 兜底本地报告
        yield {"delta": f"\n\n[在线生成失败，切换为本地模板报告。原因：{e}]\n\n"}
        yield from _local_report(prompt, ctx)
    yield {"done": True}


# --------------------------------------------------------------------------
# 本地模板兜底（无 Key / Key 失效时）
# --------------------------------------------------------------------------
def _local_report(prompt: str, ctx: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    o = ctx.get("overview", {})
    sm = o.get("summary", {})
    mmm = ctx.get("mmm", {})
    growth = ctx.get("growth", {})

    lines = [
        "## 经营策略报告（本地模板）",
        "",
        f"观察期 {o.get('period', {}).get('start', '-')} ~ {o.get('period', {}).get('end', '-')}，"
        f"平台累计 GMV {sm.get('total_gmv', '-')} 元，整体 ROAS {sm.get('roas', '-')}。",
        "",
        "## 核心结论",
        f"1. 付费渠道（搜索/广告/社媒）整体 ROAS 偏低，存在明显预算错配；自然增长与裂变渠道效率更高。",
        "2. 高价值用户贡献集中，需用 VIP 权益与复购券稳住头部；沉默高价值用户是流失预警的优先挽回对象。",
        "3. 邀请激励 ROI 存在档位差异，建议把奖励向高效档位集中，并提升邀请落地页到注册的转化。",
        "",
        "## 建议动作（按预期增量排序）",
        f"1. 预算再分配：按 MMM 建议将广告预算向高边际 ROAS 渠道迁移，预期 GMV 提升 {mmm.get('budget_plan', {}).get('gain_pct', '-')}%。",
        "2. 流失挽回：对 Top 风险名单推送定向优惠券 + 个性化内容，目标挽回率 10%~15%。",
        "3. 裂变加码：放大高效激励档位（10 人档 ROI 高），同时优化邀请注册漏斗。",
        "",
        f"（提示：本报告由本地模板生成，配置 DEEPSEEK_API_KEY 后可获得 AI 生成版。）",
    ]
    for ln in lines:
        yield {"delta": ln + "\n"}
