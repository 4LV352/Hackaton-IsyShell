from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.database import engine
from app.response import api_response


router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check API health", description="Returns basic runtime status without requiring authentication.")
def health():
    settings = get_settings()
    return api_response(
        success=True,
        status="success",
        message="API healthy",
        data={
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": {
                "backend": engine.url.get_backend_name(),
                "configured": True,
            },
            "script_base_path_exists": settings.script_base_path.exists(),
            "timestamp": datetime.now(timezone.utc),
        },
    )
