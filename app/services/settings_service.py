from __future__ import annotations

import hashlib
import secrets

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
TOKEN_HASH_PREFIX = "sha256$"


def validate_token_value(token: str) -> str:
    if not token or len(token) < 8 or len(token) > 256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token.")
    return token


def hash_token(token: str) -> str:
    token = validate_token_value(token)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{TOKEN_HASH_PREFIX}{digest}"


def stored_token_fingerprint(stored_token: str | None) -> str:
    if not stored_token:
        return ""
    if stored_token.startswith(TOKEN_HASH_PREFIX):
        return stored_token.removeprefix(TOKEN_HASH_PREFIX)[:12]
    return hashlib.sha256(stored_token.encode("utf-8")).hexdigest()[:12]


def verify_token(stored_token: str | None, provided_token: str | None) -> bool:
    if not stored_token or not provided_token:
        return False
    if stored_token.startswith(TOKEN_HASH_PREFIX):
        provided_hash = hashlib.sha256(provided_token.encode("utf-8")).hexdigest()
        return secrets.compare_digest(stored_token, f"{TOKEN_HASH_PREFIX}{provided_hash}")
    return secrets.compare_digest(stored_token, provided_token)


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
        upsert_setting(session, API_TOKEN_KEY, hash_token(token))


def update_api_token(session: Session, payload: TokenPayload) -> Setting:
    return upsert_setting(session, API_TOKEN_KEY, hash_token(payload.value))


def migrate_legacy_token_to_hash(session: Session, setting: Setting, provided_token: str) -> None:
    if setting.value.startswith(TOKEN_HASH_PREFIX):
        return
    if not secrets.compare_digest(setting.value, provided_token):
        return
    setting.value = hash_token(provided_token)
    session.commit()


def regenerate_api_token(session: Session) -> tuple[str, Setting]:
    token = secrets.token_urlsafe(32)
    setting = upsert_setting(session, API_TOKEN_KEY, hash_token(token))
    return token, setting
