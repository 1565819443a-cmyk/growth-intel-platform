"""MMM 营销组合模型 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import mmm

router = APIRouter(prefix="/api/mmm", tags=["mmm"])


@router.get("/result")
def get_mmm(db: Session = Depends(get_db)):
    """渠道贡献分解 + ROAS/边际 ROAS + 预算重分配建议。"""
    return mmm.mmm_result(db)
