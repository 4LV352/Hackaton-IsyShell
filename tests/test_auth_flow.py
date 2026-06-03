from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Client, ExecutionLog
from app.services.settings_service import seed_default_token


@pytest.fixture()
def api_client(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}, future=True)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    with testing_session() as session:
        seed_default_token(session, "test-token")
        session.add(Client(name="Cliente Teste", slug="cliente-teste", domain="teste.example.com", active=True))
        session.add(
            ExecutionLog(
                client_id=1,
                script_id=1,
                client_name="Cliente Teste",
                script_name="cleanup_logs",
                params=["cliente01"],
                status="success",
                stdout="ok",
                stderr="",
                return_code=0,
                duration_ms=10,
                requester_ip="127.0.0.1",
                token_fingerprint="abc123def456",
            )
        )
        session.add(
            ExecutionLog(
                client_id=2,
                script_id=2,
                client_name="Outro Cliente",
                script_name="backup",
                params=["cliente02"],
                status="failed",
                stdout="",
                stderr="erro",
                return_code=1,
                duration_ms=20,
                requester_ip="127.0.0.1",
                token_fingerprint="abc123def456",
            )
        )
        session.commit()

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_health_is_public(api_client: TestClient):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["version"] == "1.0.0"


def test_info_is_public(api_client: TestClient):
    response = api_client.get("/api/v1/info")

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "isy-shell-api"


def test_protected_endpoint_without_token_is_blocked(api_client: TestClient):
    response = api_client.get("/api/v1/clients")

    assert response.status_code == 401
    assert response.json()["message"] == "Header X-Isy-Token is required."
    assert response.json()["error_code"] == "TOKEN_REQUIRED"


def test_protected_endpoint_with_wrong_token_is_blocked(api_client: TestClient):
    response = api_client.get("/api/v1/clients", headers={"X-Isy-Token": "wrong-token"})

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid token."
    assert response.json()["error_code"] == "INVALID_TOKEN"


def test_protected_endpoint_with_correct_token_is_allowed(api_client: TestClient):
    response = api_client.get("/api/v1/clients", headers={"X-Isy-Token": "test-token"})

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_critical_action_without_confirm_is_blocked(api_client: TestClient):
    response = api_client.patch("/api/v1/clients/1/deactivate", headers={"X-Isy-Token": "test-token"}, json={})

    assert response.status_code == 422


def test_critical_action_with_wrong_confirm_is_blocked(api_client: TestClient):
    response = api_client.patch(
        "/api/v1/clients/1/deactivate",
        headers={"X-Isy-Token": "test-token"},
        json={"confirm": "ERRADO"},
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Confirmation required: DESATIVAR_CLIENTE."


def test_execute_script_requires_confirm(api_client: TestClient):
    response = api_client.post(
        "/api/v1/scripts/1/execute",
        headers={"X-Isy-Token": "test-token"},
        json={"client_id": 1, "params": ["cliente01"], "confirm": "ERRADO"},
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Confirmation required: EXECUTAR."


def test_regenerate_token_with_wrong_confirm_is_blocked(api_client: TestClient):
    response = api_client.post(
        "/api/v1/auth/token/regenerate",
        headers={"X-Isy-Token": "test-token"},
        json={"confirm": "ERRADO"},
    )

    assert response.status_code == 422


def test_regenerate_token_invalidates_old_token_and_allows_new_token(api_client: TestClient):
    response = api_client.post(
        "/api/v1/auth/token/regenerate",
        headers={"X-Isy-Token": "test-token"},
        json={"confirm": "REGENERAR_TOKEN"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["token"]
    assert body["token_fingerprint"]

    old_token_response = api_client.get("/api/v1/clients", headers={"X-Isy-Token": "test-token"})
    assert old_token_response.status_code == 401

    new_token_response = api_client.get("/api/v1/clients", headers={"X-Isy-Token": body["token"]})
    assert new_token_response.status_code == 200


def test_logs_can_be_filtered(api_client: TestClient):
    response = api_client.get(
        "/api/v1/logs",
        headers={"X-Isy-Token": "test-token"},
        params={"status": "success", "client_id": 1, "script_id": 1, "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "success"
    assert data[0]["client_id"] == 1
    assert data[0]["script_id"] == 1
