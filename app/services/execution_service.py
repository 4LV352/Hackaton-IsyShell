from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import ExecutionLog, Script
from app.schemas.common import ScriptExecutionRequest
from app.schemas.script import ScriptExecuteResult
from app.services.validation import ensure_safe_script_path, validate_parameter_value, validate_regex_pattern


def validate_params_with_schema(params: list[str], schema: dict) -> None:
    items = schema.get("items", [])
    if len(params) != len(items):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantidade de parâmetros incompatível com o schema permitido.",
        )

    for index, rule in enumerate(items):
        value = validate_parameter_value(params[index])
        allowed_values = rule.get("allowed_values")
        if allowed_values is not None:
            if value not in allowed_values:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parâmetro '{rule.get('name', index)}' fora da lista permitida.",
                )
            continue
        pattern = rule.get("pattern")
        if pattern is not None:
            validate_regex_pattern(pattern)
            if not re.fullmatch(pattern, value):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parâmetro '{rule.get('name', index)}' fora do padrão esperado.",
                )


def build_command(script_path: Path, params: list[str]) -> list[str]:
    return [str(script_path), *params]


def run_script(session: Session, script: Script, request_body: ScriptExecutionRequest) -> ScriptExecuteResult:
    settings = get_settings()
    if not script.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Script inativo. Ative o script antes de executar.",
        )

    validate_params_with_schema(request_body.params, script.allowed_params_schema)
    script_path = ensure_safe_script_path(settings.script_base_path, script.filename)
    command = build_command(script_path, request_body.params)

    stdout = ""
    stderr = ""
    return_code = -1
    execution_status = "falha"

    try:
        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.execution_timeout_seconds,
            check=False,
        )
        stdout = completed_process.stdout or ""
        stderr = completed_process.stderr or ""
        return_code = completed_process.returncode
        execution_status = "sucesso" if return_code == 0 else "falha"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or f"Execução excedeu {settings.execution_timeout_seconds} segundos."
        return_code = -1
        execution_status = "falha"

    log_entry = ExecutionLog(
        script_id=script.id,
        script_name=script.name,
        params=request_body.params,
        status=execution_status,
        stdout=stdout,
        stderr=stderr,
        return_code=return_code,
        executed_at=datetime.now(timezone.utc),
    )
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)

    return ScriptExecuteResult(
        script_id=script.id,
        script_name=script.name,
        params=request_body.params,
        status=execution_status,
        stdout=stdout,
        stderr=stderr,
        return_code=return_code,
        executed_at=log_entry.executed_at,
    )


def list_logs(session: Session, limit: int = 100, offset: int = 0) -> tuple[list[ExecutionLog], int]:
    from sqlalchemy import func, select

    total = session.scalar(select(func.count()).select_from(ExecutionLog)) or 0
    items = session.scalars(
        select(ExecutionLog).order_by(ExecutionLog.executed_at.desc()).offset(offset).limit(limit)
    ).all()
    return list(items), total
