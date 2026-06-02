from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import api_response
from app.core.security import require_isy_token
from app.models.entities import Script
from app.schemas.common import ScriptExecutionRequest
from app.schemas.script import ScriptCreate, ScriptRead, ScriptUpdate
from app.services.execution_service import run_script
from app.services.script_service import create_script, get_script, list_scripts, set_script_active, update_script


router = APIRouter(prefix="/scripts", tags=["Scripts"], dependencies=[Depends(require_isy_token)])


def serialize_script(script: Script) -> ScriptRead:
    return ScriptRead(
        id=script.id,
        name=script.name,
        filename=script.filename,
        description=script.description,
        allowed_params_schema=script.allowed_params_schema,
        active=script.active,
        created_at=script.created_at,
        updated_at=script.updated_at,
    )


@router.get("")
def get_scripts(session: Session = Depends(get_db)):
    scripts = [serialize_script(script).model_dump() for script in list_scripts(session)]
    return api_response(success=True, message="Scripts listados com sucesso.", data=scripts)


@router.post("")
def register_script(payload: ScriptCreate, session: Session = Depends(get_db)):
    script = create_script(session, payload)
    return api_response(success=True, message="Script cadastrado com sucesso.", data=serialize_script(script).model_dump())


@router.put("/{script_id}")
def edit_script(script_id: int, payload: ScriptUpdate, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script não encontrado.")
    updated_script = update_script(session, script, payload)
    return api_response(success=True, message="Script atualizado com sucesso.", data=serialize_script(updated_script).model_dump())


@router.patch("/{script_id}/activate")
def activate_script(script_id: int, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script não encontrado.")
    updated_script = set_script_active(session, script, True)
    return api_response(success=True, message="Script ativado com sucesso.", data=serialize_script(updated_script).model_dump())


@router.patch("/{script_id}/deactivate")
def deactivate_script(script_id: int, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script não encontrado.")
    updated_script = set_script_active(session, script, False)
    return api_response(success=True, message="Script desativado com sucesso.", data=serialize_script(updated_script).model_dump())


@router.post("/{script_id}/execute")
def execute_script(script_id: int, payload: ScriptExecutionRequest, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script não encontrado.")
    result = run_script(session, script, payload)
    return api_response(success=True, message="Execução concluída.", data=result.model_dump())
