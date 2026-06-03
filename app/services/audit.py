from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import ExecutionLog


def token_fingerprint(token: str | None) -> str:
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(password|passwd|token|secret|api_key|key)\s*=\s*([^\s&;]+)"),
    re.compile(r"(?i)\b(password|passwd|token|secret|api_key|key)\s*:\s*([^\s&;]+)"),
)


def redact_sensitive_values(text: str | None) -> str:
    if not text:
        return ""

    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def requester_ip_from_request(request: Any) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For") if request.headers else None
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", "") or ""


def create_execution_log(
    session: Session,
    *,
    client_id: int,
    script_id: int,
    client_name: str,
    script_name: str,
    params: list[str],
    status: str,
    stdout: str,
    stderr: str,
    return_code: int,
    duration_ms: int,
    requester_ip: str,
    token_value: str,
) -> ExecutionLog:
    log = ExecutionLog(
        client_id=client_id,
        script_id=script_id,
        client_name=client_name,
        script_name=script_name,
        params=params,
        status=status,
        stdout=redact_sensitive_values(stdout),
        stderr=redact_sensitive_values(stderr),
        return_code=return_code,
        duration_ms=duration_ms,
        requester_ip=requester_ip,
        token_fingerprint=token_fingerprint(token_value),
        executed_at=datetime.now(timezone.utc),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
