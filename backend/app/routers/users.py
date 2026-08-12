"""用户分层 / LTV / 流失预警 API。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import rfm, ltv, churn

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/segments")
def get_segments(db: Session = Depends(get_db)):
    """RFM 分层画像 + 分群规模/贡献。"""
    return rfm.segment_overview(db)


@router.get("/ltv/cohort")
def get_ltv_cohort(db: Session = Depends(get_db)):
    """注册队列留存率 + 人均累计 LTV 曲线。"""
    return ltv.cohort_curves(db)


@router.get("/ltv/prediction")
def get_ltv_prediction(
    horizon_days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """BG-NBD + Gamma-Gamma 未来 LTV 预测分布。"""
    return ltv.predict_ltv(db, horizon_days=horizon_days)


@router.get("/churn")
def get_churn(db: Session = Depends(get_db)):
    """流失预警模型 + Top 风险名单。"""
    return churn.churn_model(db)
