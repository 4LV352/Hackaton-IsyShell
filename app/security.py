from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.settings_service import API_TOKEN_KEY, get_setting, migrate_legacy_token_to_hash, verify_token


isy_token_header = APIKeyHeader(name="X-Isy-Token", auto_error=False)


def normalize_isy_token(value: str | None) -> str | None:
    if value is None:
        return None
    token = value.strip()
    if token.lower().startswith("x-isy-token:"):
        token = token.split(":", 1)[1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


def require_isy_token(
    x_isy_token: str | None = Security(isy_token_header),
    session: Session = Depends(get_db),
) -> None:
    token = normalize_isy_token(x_isy_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Isy-Token is required.",
        )

    token_setting = get_setting(session, API_TOKEN_KEY)
    if token_setting is None or not verify_token(token_setting.value, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    migrate_legacy_token_to_hash(session, token_setting, token)
