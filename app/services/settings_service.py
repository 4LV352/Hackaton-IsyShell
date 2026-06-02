from __future__ import annotations

try:
    from fastapi import HTTPException, status
except ModuleNotFoundError:  # pragma: no cover - fallback for local test environments
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class status:
        HTTP_409_CONFLICT = 409
        HTTP_422_UNPROCESSABLE_ENTITY = 422

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Setting
from app.schemas import TokenPayload


API_TOKEN_KEY = "api_token"


def validate_token_value(token: str) -> str:
    if not token or len(token) < 8 or len(token) > 256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token.")
    return token


def get_setting(session: Session, key: str) -> Setting | None:
    return session.scalar(select(Setting).where(Setting.key == key))


def get_setting_value(session: Session, key: str) -> str | None:
    setting = get_setting(session, key)
    return setting.value if setting else None


def upsert_setting(session: Session, key: str, value: str) -> Setting:
    setting = get_setting(session, key)
    try:
        if setting is None:
            setting = Setting(key=key, value=value)
            session.add(setting)
        else:
            setting.value = value
        session.commit()
        session.refresh(setting)
        return setting
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Configuration conflict.") from exc


def seed_default_token(session: Session, token: str) -> None:
    if get_setting(session, API_TOKEN_KEY) is None:
        upsert_setting(session, API_TOKEN_KEY, validate_token_value(token))


def update_api_token(session: Session, payload: TokenPayload) -> Setting:
    return upsert_setting(session, API_TOKEN_KEY, payload.value)
