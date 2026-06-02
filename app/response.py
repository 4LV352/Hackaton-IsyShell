from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder


def api_response(
    *,
    success: bool,
    status: str,
    message: str | None = None,
    data: Any = None,
    errors: Any = None,
):
    payload = {
        "success": success,
        "status": status,
    }
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if errors is not None:
        payload["errors"] = errors
    return jsonable_encoder(payload)
