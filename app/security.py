from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.settings_service import API_TOKEN_KEY, get_setting_value


def require_isy_token(
    x_isy_token: str | None = Header(default=None, alias="X-Isy-Token"),
    session: Session = Depends(get_db),
) -> None:
    if not x_isy_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Isy-Token is required.",
        )

    stored_token = get_setting_value(session, API_TOKEN_KEY)
    if stored_token is None or not hmac.compare_digest(stored_token, x_isy_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
