from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder


def api_response(
    *,
    success: bool,
    status: str | None = None,
    message: str | None = None,
    data: Any = None,
    errors: Any = None,
    error_code: str | None = None,
    extra: dict[str, Any] | None = None,
):
    payload = {
        "success": success,
    }
    if status is not None:
        payload["status"] = status
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if error_code is not None:
        payload["error_code"] = error_code
    if errors is not None:
        payload["errors"] = errors
    if extra is not None:
        payload.update(extra)
    return jsonable_encoder(payload)
