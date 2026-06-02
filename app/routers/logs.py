from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExecutionLog
from app.response import api_response
from app.security import require_isy_token
from app.schemas import ExecutionLogRead


router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(require_isy_token)])


def serialize_log(log: ExecutionLog) -> ExecutionLogRead:
    return ExecutionLogRead(
        id=log.id,
        client_id=log.client_id,
        script_id=log.script_id,
        client_name=log.client_name,
        script_name=log.script_name,
        params=log.params,
        status=log.status,
        stdout=log.stdout,
        stderr=log.stderr,
        return_code=log.return_code,
        duration_ms=log.duration_ms,
        requester_ip=log.requester_ip,
        token_fingerprint=log.token_fingerprint,
        executed_at=log.executed_at,
    )


@router.get("")
def get_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    rows = session.scalars(select(ExecutionLog).order_by(ExecutionLog.executed_at.desc()).offset(offset).limit(limit)).all()
    return api_response(
        success=True,
        status="success",
        message="Logs loaded",
        data=[serialize_log(row).model_dump() for row in rows],
    )


@router.get("/{log_id}")
def get_log(log_id: int, session: Session = Depends(get_db)):
    log = session.get(ExecutionLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found.")
    return api_response(success=True, status="success", message="Log loaded", data=serialize_log(log).model_dump())
