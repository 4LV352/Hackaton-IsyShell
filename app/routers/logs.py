from __future__ import annotations

from typing import Literal

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


@router.get(
    "",
    summary="List execution logs",
    description="Lists audit logs with optional filters by status, client and script.",
    responses={
        200: {
            "description": "Execution logs loaded",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "success",
                        "message": "Logs loaded",
                        "data": [
                            {
                                "id": 1,
                                "client_id": 1,
                                "script_id": 3,
                                "client_name": "Faculdade XPTO",
                                "script_name": "provisionar",
                                "params": ["cliente01", "cliente01.isy.one", "8155"],
                                "status": "success",
                                "stdout": "...",
                                "stderr": "",
                                "return_code": 0,
                                "duration_ms": 350,
                                "requester_ip": "127.0.0.1",
                                "token_fingerprint": "abc123def456",
                                "executed_at": "2026-06-03T12:00:00Z",
                            }
                        ],
                    }
                }
            },
        }
    },
)
def get_logs(
    status_filter: Literal["success", "failed"] | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None, ge=1),
    script_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    query = select(ExecutionLog)
    if status_filter is not None:
        query = query.where(ExecutionLog.status == status_filter)
    if client_id is not None:
        query = query.where(ExecutionLog.client_id == client_id)
    if script_id is not None:
        query = query.where(ExecutionLog.script_id == script_id)
    rows = session.scalars(query.order_by(ExecutionLog.executed_at.desc()).offset(offset).limit(limit)).all()
    return api_response(
        success=True,
        status="success",
        message="Logs loaded",
        data=[serialize_log(row).model_dump() for row in rows],
    )


@router.get("/{log_id}", summary="Get execution log details")
def get_log(log_id: int, session: Session = Depends(get_db)):
    log = session.get(ExecutionLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Log not found.")
    return api_response(success=True, status="success", message="Log loaded", data=serialize_log(log).model_dump())
