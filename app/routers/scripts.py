from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Script
from app.response import api_response
from app.security import require_isy_token
from app.schemas import ConfirmationPayload, ScriptCreate, ScriptExecutionRequest, ScriptRead, ScriptUpdate
from app.services.audit import requester_ip_from_request
from app.services.confirmation import require_confirmation
from app.services.script_runner import execute_script_for_client
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


@router.get(
    "",
    summary="List registered scripts",
    description="Lists scripts registered for controlled execution.",
)
def get_all_scripts(session: Session = Depends(get_db)):
    data = [serialize_script(script).model_dump() for script in list_scripts(session)]
    return api_response(success=True, status="success", message="Scripts loaded", data=data)


@router.post(
    "",
    summary="Register an allowed script",
    description="Registers a .sh file already present in the configured scripts directory.",
)
def post_script(payload: ScriptCreate, session: Session = Depends(get_db)):
    script = create_script(session, payload)
    return api_response(success=True, status="success", message="Script created", data=serialize_script(script).model_dump())


@router.get("/{script_id}", summary="Get script details")
def read_script(script_id: int, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    return api_response(success=True, status="success", message="Script loaded", data=serialize_script(script).model_dump())


@router.put("/{script_id}", summary="Update script metadata")
def put_script(script_id: int, payload: ScriptUpdate, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    updated = update_script(session, script, payload)
    return api_response(success=True, status="success", message="Script updated", data=serialize_script(updated).model_dump())


@router.patch("/{script_id}/activate", summary="Activate a script")
def activate_script(script_id: int, session: Session = Depends(get_db)):
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    updated = set_script_active(session, script, True)
    return api_response(success=True, status="success", message="Script activated", data=serialize_script(updated).model_dump())


@router.patch(
    "/{script_id}/deactivate",
    summary="Deactivate a script",
    description="Critical action. Requires body: {\"confirm\": \"DESATIVAR_SCRIPT\"}.",
    responses={
        200: {
            "description": "Script deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "success",
                        "message": "Script deactivated",
                        "data": {"id": 1, "name": "cleanup_logs", "active": False},
                    }
                }
            },
        }
    },
)
def deactivate_script(script_id: int, payload: ConfirmationPayload, session: Session = Depends(get_db)):
    require_confirmation(payload.confirm, "DESATIVAR_SCRIPT")
    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    updated = set_script_active(session, script, False)
    return api_response(success=True, status="success", message="Script deactivated", data=serialize_script(updated).model_dump())


@router.post(
    "/{script_id}/execute",
    summary="Execute an allowed script for a client",
    description="Critical action. Executes a registered .sh file only when confirm=EXECUTAR and the client-script relation is active.",
    tags=["Execução"],
    responses={
        200: {
            "description": "Script executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "success",
                        "message": "Script executed successfully",
                        "script": "provisionar",
                        "client": "Faculdade XPTO",
                        "return_code": 0,
                        "stdout": "[1/4] Preparando provisionamento...",
                        "stderr": "",
                        "duration_ms": 350,
                        "log_id": 1,
                    }
                }
            },
        },
        422: {
            "description": "Missing or invalid confirmation",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status": "failed",
                        "message": "Confirmation required: EXECUTAR.",
                        "error_code": "CONFIRMATION_REQUIRED",
                    }
                }
            },
        },
    },
)
def execute_script(script_id: int, payload: ScriptExecutionRequest, request: Request, session: Session = Depends(get_db)):
    require_confirmation(payload.confirm, "EXECUTAR")
    token_value = request.headers.get("X-Isy-Token", "")
    requester_ip = requester_ip_from_request(request)
    code, body = execute_script_for_client(
        session,
        script_id=script_id,
        client_id=payload.client_id,
        params=payload.params,
        requester_ip=requester_ip,
        token_value=token_value,
    )
    return JSONResponse(status_code=code, content=body)
