from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_isy_token
from app.schemas import TokenRegenerateRequest
from app.services.settings_service import (
    API_TOKEN_KEY,
    get_setting_value,
    regenerate_api_token,
    stored_token_fingerprint,
)


router = APIRouter(prefix="/auth", tags=["Auth"], dependencies=[Depends(require_isy_token)])


@router.get(
    "/token/status",
    summary="Get token status",
    description="Returns whether an API token is configured and its fingerprint. Never returns the raw token.",
    responses={
        200: {
            "description": "Token status",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Token ativo",
                        "data": {
                            "token_configured": True,
                            "token_fingerprint": "abc123def456",
                        },
                    }
                }
            },
        }
    },
)
def get_token_status(session: Session = Depends(get_db)):
    stored_token = get_setting_value(session, API_TOKEN_KEY)
    token_configured = stored_token is not None
    return {
        "success": True,
        "message": "Token ativo" if token_configured else "Token nao configurado",
        "data": {
            "token_configured": token_configured,
            "token_fingerprint": stored_token_fingerprint(stored_token),
        },
    }


@router.post(
    "/token/regenerate",
    summary="Regenerate API token",
    description=(
        "Critical action. Requires the current X-Isy-Token and body "
        "{\"confirm\": \"REGENERAR_TOKEN\"}. The new token is returned only once."
    ),
    responses={
        200: {
            "description": "Token regenerated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Token regenerado com sucesso. Copie agora, ele nao sera exibido novamente.",
                        "data": {
                            "token": "novo-token-gerado",
                            "token_fingerprint": "abc123def456",
                        },
                        "token": "novo-token-gerado",
                        "token_fingerprint": "abc123def456",
                    }
                }
            },
        }
    },
)
def regenerate_token(payload: TokenRegenerateRequest, session: Session = Depends(get_db)):
    token, setting = regenerate_api_token(session)
    return {
        "success": True,
        "message": "Token regenerado com sucesso. Copie agora, ele nao sera exibido novamente.",
        "data": {
            "token": token,
            "token_fingerprint": stored_token_fingerprint(setting.value),
        },
        "token": token,
        "token_fingerprint": stored_token_fingerprint(setting.value),
    }
