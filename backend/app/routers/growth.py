"""裂变增长归因 API。"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import growth_attribution

router = APIRouter(prefix="/api/growth", tags=["growth"])


@router.get("/summary")
def get_growth_summary(db: Session = Depends(get_db)):
    """K 因子趋势 / 激励阶梯 ROI / 裂变漏斗 / Top 邀请人。"""
    return growth_attribution.growth_summary(db)


@router.get("/tree")
def get_invite_tree(
    inviter_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    """邀请关系网络（图谱数据）。"""
    return growth_attribution.invite_tree(db, inviter_id=inviter_id)
