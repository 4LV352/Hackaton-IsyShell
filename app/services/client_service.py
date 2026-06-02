from __future__ import annotations

import re
import unicodedata

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
        HTTP_404_NOT_FOUND = 404
        HTTP_422_UNPROCESSABLE_ENTITY = 422

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Client, ClientScript, Script
from app.schemas import ClientCreate, ClientUpdate


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid client name.")
    return slug


def list_clients(session: Session) -> list[Client]:
    return list(session.scalars(select(Client).order_by(Client.id)).all())


def get_client(session: Session, client_id: int) -> Client | None:
    return session.get(Client, client_id)


def create_client(session: Session, payload: ClientCreate) -> Client:
    client = Client(
        name=payload.name,
        slug=payload.slug or slugify(payload.name),
        domain=payload.domain,
        active=payload.active,
    )
    try:
        session.add(client)
        session.commit()
        session.refresh(client)
        return client
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists.") from exc


def update_client(session: Session, client: Client, payload: ClientUpdate) -> Client:
    if payload.name is not None:
        client.name = payload.name
    if payload.slug is not None:
        client.slug = payload.slug
    elif payload.name is not None and payload.slug is None:
        client.slug = slugify(payload.name)
    if payload.domain is not None:
        client.domain = payload.domain
    if payload.active is not None:
        client.active = payload.active
    try:
        session.commit()
        session.refresh(client)
        return client
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client already exists.") from exc


def set_client_active(session: Session, client: Client, active: bool) -> Client:
    client.active = active
    session.commit()
    session.refresh(client)
    return client


def get_client_script(session: Session, client_id: int, script_id: int) -> ClientScript | None:
    return session.scalar(
        select(ClientScript).where(
            ClientScript.client_id == client_id,
            ClientScript.script_id == script_id,
        )
    )


def set_client_script_active(session: Session, client_id: int, script_id: int, active: bool) -> ClientScript:
    relation = get_client_script(session, client_id, script_id)
    if relation is None:
        relation = ClientScript(client_id=client_id, script_id=script_id, active=active)
        session.add(relation)
    else:
        relation.active = active
    session.commit()
    session.refresh(relation)
    return relation


def list_client_scripts(session: Session, client_id: int) -> list[ClientScript]:
    return list(
        session.scalars(
            select(ClientScript).where(ClientScript.client_id == client_id).order_by(ClientScript.created_at.asc())
        ).all()
    )


def get_active_client_with_script(session: Session, client_id: int, script_id: int) -> tuple[Client | None, Script | None]:
    client = session.get(Client, client_id)
    script = session.get(Script, script_id)
    return client, script


def create_or_activate_client_script(session: Session, client_id: int, script_id: int) -> ClientScript:
    relation = get_client_script(session, client_id, script_id)
    if relation is None:
        relation = ClientScript(client_id=client_id, script_id=script_id, active=True)
        session.add(relation)
    else:
        relation.active = True
    session.commit()
    session.refresh(relation)
    return relation


def deactivate_client_script(session: Session, client_id: int, script_id: int) -> ClientScript:
    relation = get_client_script(session, client_id, script_id)
    if relation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client-script relation not found.")
    relation.active = False
    session.commit()
    session.refresh(relation)
    return relation
