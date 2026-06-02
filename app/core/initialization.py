from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Script
from app.services.settings_service import seed_default_token


def ensure_scripts_directory() -> Path:
    settings = get_settings()
    settings.script_base_path.mkdir(parents=True, exist_ok=True)
    for script_file in settings.script_base_path.glob("*.sh"):
        script_file.chmod(0o755)
    return settings.script_base_path


def seed_demo_scripts(session: Session) -> None:
    settings = get_settings()
    samples = [
        {
            "name": "cleanup_logs",
            "filename": "cleanup_logs.sh",
            "description": "Simula limpeza de logs de um cliente.",
            "allowed_params_schema": {
                "type": "array",
                "items": [
                    {
                        "name": "cliente",
                        "pattern": "^[a-zA-Z0-9_-]{1,32}$",
                        "required": True,
                        "description": "Identificador do cliente.",
                    }
                ],
            },
        },
        {
            "name": "docker_status",
            "filename": "docker_status.sh",
            "description": "Simula checagem de containers Docker.",
            "allowed_params_schema": {"type": "array", "items": []},
        },
        {
            "name": "provisionar",
            "filename": "provisionar.sh",
            "description": "Simula provisionamento de ambiente.",
            "allowed_params_schema": {
                "type": "array",
                "items": [
                    {
                        "name": "cliente",
                        "pattern": "^[a-zA-Z0-9_-]{1,32}$",
                        "required": True,
                    },
                    {
                        "name": "dominio",
                        "pattern": "^[a-zA-Z0-9.-]{1,253}$",
                        "required": True,
                    },
                    {
                        "name": "porta",
                        "pattern": "^[0-9]{2,5}$",
                        "required": True,
                    },
                ],
            },
        },
    ]

    existing_filenames = set(session.scalars(select(Script.filename)).all())
    for sample in samples:
        if sample["filename"] in existing_filenames:
            continue
        script_path = settings.script_base_path / sample["filename"]
        if not script_path.is_file():
            continue
        script = Script(
            name=sample["name"],
            filename=sample["filename"],
            description=sample["description"],
            allowed_params_schema=sample["allowed_params_schema"],
            active=True,
        )
        session.add(script)
    session.commit()


def initialize_database(session_factory) -> None:
    from app.core.database import Base, engine

    ensure_scripts_directory()
    Base.metadata.create_all(bind=engine)
    with session_factory() as session:
        settings = get_settings()
        seed_default_token(session, settings.api_token)
        seed_demo_scripts(session)
