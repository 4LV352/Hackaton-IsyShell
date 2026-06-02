from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.response import api_response


router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    settings = get_settings()
    return api_response(
        success=True,
        message="API saudável.",
        data={
            "status": "ok",
            "service": settings.app_name,
            "timestamp": datetime.now(timezone.utc),
        },
    )
