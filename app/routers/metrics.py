from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.response import api_response
from app.security import require_isy_token
from app.schemas import MetricsRead
from app.services.metrics_service import get_metrics


router = APIRouter(prefix="/metrics", tags=["Métricas"], dependencies=[Depends(require_isy_token)])


@router.get("", summary="Get operational metrics")
def metrics(session: Session = Depends(get_db)):
    data = MetricsRead(**get_metrics(session)).model_dump()
    return api_response(success=True, status="success", message="Metrics loaded", data=data)
