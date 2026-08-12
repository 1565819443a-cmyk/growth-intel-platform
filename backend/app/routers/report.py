"""AI 策略报告 API（SSE 流式）。"""
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import report_gen

router = APIRouter(prefix="/api/report", tags=["report"])


class ReportRequest(BaseModel):
    """前端传入各模块分析结果，后端组装 prompt 后流式生成报告。"""
    overview: Optional[Dict[str, Any]] = None
    users: Optional[Dict[str, Any]] = None
    mmm: Optional[Dict[str, Any]] = None
    growth: Optional[Dict[str, Any]] = None


@router.post("")
def generate_report(req: ReportRequest):
    ctx = {
        "overview": req.overview or {},
        "users": req.users or {},
        "mmm": req.mmm or {},
        "growth": req.growth or {},
    }

    def gen():
        for item in report_gen.stream_report(ctx):
            # 统一输出为 SSE 的 data 字段
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
