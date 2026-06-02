from typing import Any

from fastapi.encoders import jsonable_encoder


def api_response(
    *,
    success: bool,
    message: str,
    data: Any = None,
    errors: Any = None,
):
    payload = {
        "success": success,
        "message": message,
        "data": data,
    }
    if errors is not None:
        payload["errors"] = errors
    return jsonable_encoder(payload)
