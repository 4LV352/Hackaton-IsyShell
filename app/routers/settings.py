from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.response import api_response
from app.security import require_isy_token
from app.schemas import TokenPayload
from app.services.settings_service import API_TOKEN_KEY, get_setting_value, stored_token_fingerprint, update_api_token


router = APIRouter(prefix="/settings", tags=["Auth"], dependencies=[Depends(require_isy_token)])


@router.get("/token", summary="Get token fingerprint")
def get_token(session: Session = Depends(get_db)):
    token = get_setting_value(session, API_TOKEN_KEY)
    return api_response(
        success=True,
        status="success",
        message="Token fingerprint loaded",
        data={"key": API_TOKEN_KEY, "fingerprint": stored_token_fingerprint(token)},
    )


@router.put("/token", summary="Rotate API token")
def put_token(payload: TokenPayload, session: Session = Depends(get_db)):
    setting = update_api_token(session, payload)
    return api_response(
        success=True,
        status="success",
        message="Token updated",
        data={"key": setting.key, "fingerprint": stored_token_fingerprint(setting.value)},
    )
