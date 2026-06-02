from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
import shutil
import os

try:
    from fastapi import HTTPException, status
except ModuleNotFoundError:  # pragma: no cover - fallback for local test environments
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class status:
        HTTP_400_BAD_REQUEST = 400
        HTTP_404_NOT_FOUND = 404
        HTTP_409_CONFLICT = 409
        HTTP_422_UNPROCESSABLE_ENTITY = 422
        HTTP_500_INTERNAL_SERVER_ERROR = 500

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Client, ClientScript, Script
from app.schemas import ScriptExecutionRequest
from app.services.audit import create_execution_log


CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def validate_filename(filename: str) -> str:
    if not filename or not re.fullmatch(r"[A-Za-z0-9_.-]+\.sh", filename):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid filename.")
    return filename


def resolve_script_path(base_path: Path, filename: str) -> Path:
    safe_filename = validate_filename(filename)
    base = base_path.resolve()
    candidate = (base / safe_filename).resolve()
    if not candidate.is_relative_to(base):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal blocked.")
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script file not found.")
    return candidate


def validate_param_value(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 255 or CONTROL_CHARS.search(value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid parameter.")
    return value


def validate_params_against_schema(params: list[str], schema: dict) -> None:
    items = schema.get("items", [])
    if len(params) != len(items):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parameters do not match allowed schema.",
        )

    for index, rule in enumerate(items):
        value = validate_param_value(params[index])
        allowed_values = rule.get("allowed_values")
        if allowed_values is not None:
            if value not in allowed_values:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter '{rule.get('name', index)}' not allowed.",
                )
            continue
        pattern = rule.get("pattern")
        if pattern is not None and not re.fullmatch(pattern, value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parameter '{rule.get('name', index)}' does not match expected pattern.",
            )


def build_command(script_path: Path, params: list[str]) -> list[str]:
    return [str(script_path), *params]


def resolve_execution_command(script_path: Path, params: list[str]) -> list[str]:
    settings = get_settings()
    if settings.environment == "development" and os.name == "nt":
        bash_executable = (
            os.getenv("BASH_EXECUTABLE")
            or shutil.which("bash")
            or shutil.which("sh")
        )
        if bash_executable is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Windows development mode requires Bash (Git Bash, MSYS2 or WSL) to execute .sh scripts.",
            )
        return [bash_executable, str(script_path), *params]
    return build_command(script_path, params)


def get_client_script_relation(session: Session, client_id: int, script_id: int) -> ClientScript | None:
    return session.scalar(
        select(ClientScript).where(
            ClientScript.client_id == client_id,
            ClientScript.script_id == script_id,
        )
    )


def execute_script_for_client(
    session: Session,
    *,
    script_id: int,
    client_id: int,
    params: list[str],
    requester_ip: str,
    token_value: str,
) -> tuple[int, dict]:
    settings = get_settings()
    started_at = time.perf_counter()

    client = session.get(Client, client_id)
    script = session.get(Script, script_id)
    client_name = client.name if client else f"client-{client_id}"
    script_name = script.name if script else f"script-{script_id}"

    if client is None:
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client_name,
            script_name=script_name,
            params=params,
            status="failed",
            stdout="",
            stderr="Client not found.",
            return_code=404,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 404, {
            "success": False,
            "status": "failed",
            "message": "Client not found",
            "return_code": 404,
            "stdout": "",
            "stderr": "Client not found.",
            "log_id": log.id,
        }

    if not client.active:
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script_name,
            params=params,
            status="failed",
            stdout="",
            stderr="Client inactive.",
            return_code=403,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 403, {
            "success": False,
            "status": "failed",
            "message": "Client inactive",
            "return_code": 403,
            "stdout": "",
            "stderr": "Client inactive.",
            "log_id": log.id,
        }

    if script is None:
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script_name,
            params=params,
            status="failed",
            stdout="",
            stderr="Script not found.",
            return_code=404,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 404, {
            "success": False,
            "status": "failed",
            "message": "Script not found",
            "return_code": 404,
            "stdout": "",
            "stderr": "Script not found.",
            "log_id": log.id,
        }

    if not script.active:
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status="failed",
            stdout="",
            stderr="Script inactive.",
            return_code=409,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 409, {
            "success": False,
            "status": "failed",
            "message": "Script inactive",
            "return_code": 409,
            "stdout": "",
            "stderr": "Script inactive.",
            "log_id": log.id,
        }

    relation = get_client_script_relation(session, client_id, script_id)
    if relation is None or not relation.active:
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status="failed",
            stdout="",
            stderr="Script not allowed for this client.",
            return_code=403,
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 403, {
            "success": False,
            "status": "failed",
            "message": "Script not allowed for this client",
            "return_code": 403,
            "stdout": "",
            "stderr": "Script not allowed for this client.",
            "log_id": log.id,
        }

    try:
        validate_params_against_schema(params, script.allowed_params_schema)
        script_path = resolve_script_path(settings.script_base_path, script.filename)
    except HTTPException as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        detail = str(exc.detail)
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status="failed",
            stdout="",
            stderr=detail,
            return_code=exc.status_code,
            duration_ms=duration_ms,
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return exc.status_code, {
            "success": False,
            "status": "failed",
            "message": detail,
            "return_code": exc.status_code,
            "stdout": "",
            "stderr": detail,
            "log_id": log.id,
        }

    command = resolve_execution_command(script_path, params)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings.script_timeout_seconds,
            check=False,
        )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return_code = completed.returncode
        status_value = "success" if return_code == 0 else "failed"
        message = "Script executed successfully" if return_code == 0 else "Script execution failed"
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status=status_value,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            duration_ms=duration_ms,
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return (200 if return_code == 0 else 400), {
            "success": return_code == 0,
            "status": status_value,
            "message": message,
            "script": script.name,
            "client": client.name,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "log_id": log.id,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        stdout = exc.stdout or ""
        stderr = exc.stderr or "Execution timed out"
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status="failed",
            stdout=stdout,
            stderr=stderr,
            return_code=124,
            duration_ms=duration_ms,
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 504, {
            "success": False,
            "status": "failed",
            "message": "Script execution failed",
            "script": script.name,
            "client": client.name,
            "return_code": 124,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "log_id": log.id,
        }
    except (FileNotFoundError, PermissionError, OSError) as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log = create_execution_log(
            session,
            client_id=client_id,
            script_id=script_id,
            client_name=client.name,
            script_name=script.name,
            params=params,
            status="failed",
            stdout="",
            stderr=str(exc),
            return_code=127,
            duration_ms=duration_ms,
            requester_ip=requester_ip,
            token_value=token_value,
        )
        return 500, {
            "success": False,
            "status": "failed",
            "message": "Script execution failed",
            "script": script.name,
            "client": client.name,
            "return_code": 127,
            "stdout": "",
            "stderr": str(exc),
            "duration_ms": duration_ms,
            "log_id": log.id,
        }
