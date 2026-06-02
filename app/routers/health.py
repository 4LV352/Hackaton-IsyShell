from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import get_settings
from app.response import api_response


router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    settings = get_settings()
    return api_response(
        success=True,
        status="success",
        message="API healthy",
        data={
            "service": settings.app_name,
            "timestamp": datetime.now(timezone.utc),
        },
    )
