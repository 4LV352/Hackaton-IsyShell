from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import api_response
from app.core.security import require_isy_token
from app.schemas.common import TokenValueRequest
from app.services.settings_service import API_TOKEN_KEY, get_setting_value, update_api_token


router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(require_isy_token)])


@router.get("/token")
def get_token(session: Session = Depends(get_db)):
    value = get_setting_value(session, API_TOKEN_KEY)
    return api_response(
        success=True,
        message="Token carregado com sucesso.",
        data={"key": API_TOKEN_KEY, "value": value},
    )


@router.put("/token")
def put_token(payload: TokenValueRequest, session: Session = Depends(get_db)):
    setting = update_api_token(session, payload)
    return api_response(
        success=True,
        message="Token atualizado com sucesso.",
        data={"key": setting.key, "value": setting.value},
    )
