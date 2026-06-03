from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Client, ExecutionLog, Script


def get_metrics(session: Session) -> dict:
    total_executions = session.scalar(select(func.count()).select_from(ExecutionLog)) or 0
    successful_executions = session.scalar(
        select(func.count()).select_from(ExecutionLog).where(ExecutionLog.status == "success")
    ) or 0
    failed_executions = session.scalar(
        select(func.count()).select_from(ExecutionLog).where(ExecutionLog.status == "failed")
    ) or 0

    now_utc = datetime.now(timezone.utc)
    day_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    executions_today = session.scalar(
        select(func.count()).select_from(ExecutionLog).where(ExecutionLog.executed_at >= day_start)
    ) or 0

    last_log = session.scalar(select(ExecutionLog).order_by(ExecutionLog.executed_at.desc()).limit(1))
    active_clients = session.scalar(select(func.count()).select_from(Client).where(Client.active.is_(True))) or 0
    active_scripts = session.scalar(select(func.count()).select_from(Script).where(Script.active.is_(True))) or 0
    average_duration_ms = session.scalar(select(func.avg(ExecutionLog.duration_ms)).select_from(ExecutionLog)) or 0

    success_rate = 0.0
    if total_executions:
        success_rate = round((successful_executions / total_executions) * 100, 2)

    return {
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "failed_executions": failed_executions,
        "success_rate": success_rate,
        "average_duration_ms": round(float(average_duration_ms), 2),
        "executions_today": executions_today,
        "last_script_executed": None
        if last_log is None
        else {
            "log_id": last_log.id,
            "script_id": last_log.script_id,
            "script_name": last_log.script_name,
            "client_id": last_log.client_id,
            "client_name": last_log.client_name,
            "executed_at": last_log.executed_at,
        },
        "active_clients": active_clients,
        "active_scripts": active_scripts,
    }
