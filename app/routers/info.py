from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.response import api_response


router = APIRouter(prefix="/info", tags=["Health"])


@router.get(
    "",
    summary="Get API information",
    description="Public metadata endpoint for demos and operational checks.",
    responses={
        200: {
            "description": "API metadata",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "API information loaded",
                        "data": {
                            "name": "isy-shell-api",
                            "version": "1.0.0",
                            "description": "API segura para executar scripts Bash autorizados por cliente.",
                            "environment": "development",
                            "docs_url": "/docs",
                            "health_url": "/health",
                        },
                    }
                }
            },
        }
    },
)
def info():
    settings = get_settings()
    return api_response(
        success=True,
        status="success",
        message="API information loaded",
        data={
            "name": settings.app_name,
            "version": settings.app_version,
            "description": settings.app_description,
            "environment": settings.environment,
            "docs_url": "/docs",
            "health_url": "/health",
        },
    )
