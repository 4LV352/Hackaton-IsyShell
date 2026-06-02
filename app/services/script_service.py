from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Script
from app.schemas import AllowedParamsSchema, ScriptCreate, ScriptUpdate
from app.services.script_runner import resolve_script_path, validate_filename


def list_scripts(session: Session) -> list[Script]:
    return list(session.scalars(select(Script).order_by(Script.id)).all())


def get_script(session: Session, script_id: int) -> Script | None:
    return session.get(Script, script_id)


def create_script(session: Session, payload: ScriptCreate) -> Script:
    settings = get_settings()
    filename = validate_filename(payload.filename)
    resolve_script_path(settings.script_base_path, filename)
    script = Script(
        name=payload.name,
        filename=filename,
        description=payload.description,
        allowed_params_schema=payload.allowed_params_schema.model_dump(),
        active=payload.active,
    )
    try:
        session.add(script)
        session.commit()
        session.refresh(script)
        return script
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Script already exists.") from exc


def update_script(session: Session, script: Script, payload: ScriptUpdate) -> Script:
    settings = get_settings()
    if payload.name is not None:
        script.name = payload.name
    if payload.filename is not None:
        filename = validate_filename(payload.filename)
        resolve_script_path(settings.script_base_path, filename)
        script.filename = filename
    if payload.description is not None:
        script.description = payload.description
    if payload.allowed_params_schema is not None:
        script.allowed_params_schema = payload.allowed_params_schema.model_dump()
    if payload.active is not None:
        script.active = payload.active
    try:
        session.commit()
        session.refresh(script)
        return script
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Script already exists.") from exc


def set_script_active(session: Session, script: Script, active: bool) -> Script:
    script.active = active
    session.commit()
    session.refresh(script)
    return script
