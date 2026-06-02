from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.response import api_response
from app.security import require_isy_token
from app.schemas import ClientCreate, ClientRead, ClientUpdate
from app.services.client_service import (
    create_or_activate_client_script,
    create_client,
    deactivate_client_script as deactivate_client_script_relation,
    get_client,
    list_client_scripts,
    list_clients,
    set_client_active,
    set_client_script_active,
    update_client,
)
from app.services.script_service import get_script


router = APIRouter(prefix="/clients", tags=["Clients"], dependencies=[Depends(require_isy_token)])


def serialize_client(client: Client) -> ClientRead:
    return ClientRead(
        id=client.id,
        name=client.name,
        slug=client.slug,
        domain=client.domain,
        active=client.active,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.get("")
def get_all_clients(session: Session = Depends(get_db)):
    data = [serialize_client(client).model_dump() for client in list_clients(session)]
    return api_response(success=True, status="success", message="Clients loaded", data=data)


@router.post("")
def post_client(payload: ClientCreate, session: Session = Depends(get_db)):
    client = create_client(session, payload)
    return api_response(success=True, status="success", message="Client created", data=serialize_client(client).model_dump())


@router.get("/{client_id}")
def read_client(client_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    return api_response(success=True, status="success", message="Client loaded", data=serialize_client(client).model_dump())


@router.put("/{client_id}")
def put_client(client_id: int, payload: ClientUpdate, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    updated = update_client(session, client, payload)
    return api_response(success=True, status="success", message="Client updated", data=serialize_client(updated).model_dump())


@router.patch("/{client_id}/activate")
def activate_client(client_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    updated = set_client_active(session, client, True)
    return api_response(success=True, status="success", message="Client activated", data=serialize_client(updated).model_dump())


@router.patch("/{client_id}/deactivate")
def deactivate_client(client_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    updated = set_client_active(session, client, False)
    return api_response(success=True, status="success", message="Client deactivated", data=serialize_client(updated).model_dump())


@router.patch("/{client_id}/scripts/{script_id}/activate")
def activate_client_script(client_id: int, script_id: int, session: Session = Depends(get_db)):
    if get_client(session, client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if get_script(session, script_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    relation = set_client_script_active(session, client_id, script_id, True)
    return api_response(success=True, status="success", message="Client script activated", data={"id": relation.id, "client_id": client_id, "script_id": script_id, "active": relation.active})


@router.patch("/{client_id}/scripts/{script_id}/deactivate")
def deactivate_client_script(client_id: int, script_id: int, session: Session = Depends(get_db)):
    if get_client(session, client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if get_script(session, script_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    relation = set_client_script_active(session, client_id, script_id, False)
    return api_response(success=True, status="success", message="Client script deactivated", data={"id": relation.id, "client_id": client_id, "script_id": script_id, "active": relation.active})


@router.get("/{client_id}/scripts")
def get_client_scripts(client_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if not client.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client inactive.")

    data = [
        {
            "id": relation.id,
            "client_id": relation.client_id,
            "script_id": relation.script_id,
            "script_name": relation.script.name if relation.script else None,
            "active": relation.active,
            "created_at": relation.created_at,
        }
        for relation in list_client_scripts(session, client_id)
    ]
    return api_response(success=True, status="success", message="Client scripts loaded", data=data)


@router.post("/{client_id}/scripts/{script_id}")
def create_client_script_relation(client_id: int, script_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if not client.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client inactive.")

    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    if not script.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Script inactive.")

    relation = create_or_activate_client_script(session, client_id, script_id)
    return api_response(
        success=True,
        status="success",
        message="Client-script relation enabled",
        data={"id": relation.id, "client_id": client_id, "script_id": script_id, "active": relation.active},
    )


@router.delete("/{client_id}/scripts/{script_id}")
def delete_client_script_relation(client_id: int, script_id: int, session: Session = Depends(get_db)):
    client = get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    if not client.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client inactive.")

    script = get_script(session, script_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found.")
    if not script.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Script inactive.")

    relation = deactivate_client_script_relation(session, client_id, script_id)
    return api_response(
        success=True,
        status="success",
        message="Client-script relation disabled",
        data={"id": relation.id, "client_id": client_id, "script_id": script_id, "active": relation.active},
    )
