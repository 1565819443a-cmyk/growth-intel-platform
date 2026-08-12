"""总览 API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import overview as overview_svc

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def get_overview(db: Session = Depends(get_db)):
    return overview_svc.overview(db)
