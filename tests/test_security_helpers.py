from pathlib import Path

import pytest

from app.config import get_settings
from app.models import ClientScript
from app.services.audit import redact_sensitive_values, token_fingerprint
from app.services.client_service import create_or_activate_client_script, deactivate_client_script, slugify
from app.services.script_runner import (
    HTTPException,
    build_command,
    resolve_execution_command,
    resolve_script_path,
    validate_filename,
    validate_params_against_schema,
)


def test_validate_filename_blocks_traversal():
    assert validate_filename("cleanup_logs.sh") == "cleanup_logs.sh"


def test_resolve_script_path_blocks_traversal():
    with pytest.raises(HTTPException):
        resolve_script_path(Path("/opt/isyone/scripts"), "../secret.sh")


def test_slugify_normalizes_name():
    assert slugify("Faculdade XPTO") == "faculdade-xpto"
    assert slugify("Clínica Beta") == "clinica-beta"


def test_token_fingerprint_is_short():
    fingerprint = token_fingerprint("change-me-token")
    assert len(fingerprint) == 12


def test_redact_sensitive_values_masks_common_secrets():
    text = "password=abc passwd:xyz token=123 secret=top api_key=key123 key=raw"

    assert redact_sensitive_values(text) == (
        "password=[REDACTED] passwd=[REDACTED] token=[REDACTED] "
        "secret=[REDACTED] api_key=[REDACTED] key=[REDACTED]"
    )


def test_development_settings_use_sqlite(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SCRIPT_BASE_PATH", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url.startswith("sqlite:///")
    assert str(settings.script_base_path).endswith("scripts")


def test_production_settings_use_postgres(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SCRIPT_BASE_PATH", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url.startswith("postgresql")
    assert settings.script_base_path.as_posix() == "/opt/isyone/scripts"


def test_validate_params_against_schema_accepts_valid_values():
    schema = {
        "items": [
            {"name": "client", "pattern": "^[a-zA-Z0-9_-]{1,32}$"},
            {"name": "domain", "pattern": "^[a-zA-Z0-9.-]{1,253}$"},
        ]
    }
    validate_params_against_schema(["cliente01", "cliente01.example.com"], schema)
    assert build_command("/opt/isyone/scripts/provisionar.sh", ["cliente01", "cliente01.example.com"]) == [
        "/opt/isyone/scripts/provisionar.sh",
        "cliente01",
        "cliente01.example.com",
    ]


def test_resolve_execution_command_uses_bash_on_windows_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BASH_EXECUTABLE", r"C:\Program Files\Git\bin\bash.exe")
    monkeypatch.setattr("app.services.script_runner.os.name", "nt", raising=False)
    get_settings.cache_clear()

    command = resolve_execution_command(Path("C:/scripts/cleanup_logs.sh"), ["cliente01"])

    assert command == [r"C:\Program Files\Git\bin\bash.exe", str(Path("C:/scripts/cleanup_logs.sh")), "cliente01"]


def test_client_script_relation_helpers_activate_and_deactivate(monkeypatch):
    class DummySession:
        def __init__(self):
            self.commits = 0
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            self.commits += 1

        def refresh(self, obj):
            return obj

    session = DummySession()
    relation = ClientScript(client_id=1, script_id=2, active=False)

    monkeypatch.setattr("app.services.client_service.get_client_script", lambda _session, client_id, script_id: None)
    created = create_or_activate_client_script(session, 1, 2)

    assert created.active is True
    assert created.client_id == 1
    assert created.script_id == 2
    assert session.commits == 1
    assert len(session.added) == 1

    monkeypatch.setattr("app.services.client_service.get_client_script", lambda _session, client_id, script_id: relation)
    updated = deactivate_client_script(session, 1, 2)

    assert updated.active is False
    assert session.commits == 2
