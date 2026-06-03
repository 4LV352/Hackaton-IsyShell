from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Client, ClientScript, Script
from app.response import api_response
from app.routers.auth import router as auth_router
from app.routers.clients import router as clients_router
from app.routers.health import router as health_router
from app.routers.info import router as info_router
from app.routers.logs import router as logs_router
from app.routers.metrics import router as metrics_router
from app.routers.scripts import router as scripts_router
from app.routers.settings import router as settings_router
from app.schemas import AllowedParamsSchema, ClientCreate, ParameterRule, ScriptCreate
from app.services.client_service import create_client, set_client_script_active
from app.services.script_service import create_script
from app.services.settings_service import seed_default_token
from app.services.script_runner import validate_filename


settings = get_settings()
logger = logging.getLogger(__name__)

OPENAPI_DESCRIPTION = """
IsyShell substitui a execucao manual via SSH por uma API segura para scripts Bash autorizados por cliente.

Fluxo da demo:
1. Autentique com `X-Isy-Token`.
2. Liste clientes e scripts.
3. Veja scripts permitidos para um cliente.
4. Execute um script autorizado.
5. Consulte logs auditaveis e metricas operacionais.
"""

TAGS_METADATA = [
    {"name": "Health", "description": "Status operacional da API."},
    {"name": "Auth", "description": "Status e regeneracao manual do token da API."},
    {"name": "Clientes", "description": "Cadastro de clientes e vinculos cliente-script."},
    {"name": "Scripts", "description": "Cadastro e execucao segura de scripts autorizados."},
    {"name": "Execução", "description": "Execucao confirmada de scripts autorizados por cliente."},
    {"name": "Logs", "description": "Auditoria das execucoes com stdout/stderr redigidos."},
    {"name": "Métricas", "description": "Indicadores operacionais para acompanhamento da plataforma."},
]

app = FastAPI(
    title=settings.app_name,
    description=OPENAPI_DESCRIPTION,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
)


def _http_error_code(detail: object, status_code: int) -> str:
    message = str(detail)
    if status_code == 401 and "required" in message.lower():
        return "TOKEN_REQUIRED"
    if status_code == 401:
        return "INVALID_TOKEN"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "CONFLICT"
    if message.startswith("Confirmation required"):
        return "CONFIRMATION_REQUIRED"
    if status_code == 422:
        return "VALIDATION_ERROR"
    return "HTTP_ERROR"


def _ensure_base_scripts() -> None:
    settings.script_base_path.mkdir(parents=True, exist_ok=True)
    for script_file in settings.script_base_path.glob("*.sh"):
        try:
            script_file.chmod(0o755)
        except OSError:
            pass


def _warn_missing_script(filename: str) -> None:
    logger.warning("Expected script file missing from %s: %s", settings.script_base_path, filename)


def _seed_scripts_and_clients() -> None:
    _ensure_base_scripts()
    Base.metadata.create_all(bind=engine)

    demo_scripts = [
        {
            "name": "cleanup_logs",
            "filename": "cleanup_logs.sh",
            "description": "Simulated log cleanup",
            "allowed_params_schema": AllowedParamsSchema(
                items=[ParameterRule(name="client", pattern="^[a-zA-Z0-9_-]{1,32}$")]
            ),
        },
        {
            "name": "docker_status",
            "filename": "docker_status.sh",
            "description": "Simulated docker container check",
            "allowed_params_schema": AllowedParamsSchema(
                items=[ParameterRule(name="client", pattern="^[a-zA-Z0-9_-]{1,32}$")]
            ),
        },
        {
            "name": "provisionar",
            "filename": "provisionar.sh",
            "description": "Simulated environment provisioning",
            "allowed_params_schema": AllowedParamsSchema(
                items=[
                    ParameterRule(name="client", pattern="^[a-zA-Z0-9_-]{1,32}$"),
                    ParameterRule(name="domain", pattern="^[a-zA-Z0-9.-]{1,253}$"),
                    ParameterRule(name="port", pattern="^[0-9]{2,5}$"),
                ]
            ),
        },
        {
            "name": "backup",
            "filename": "backup.sh",
            "description": "Simulated backup",
            "allowed_params_schema": AllowedParamsSchema(
                items=[ParameterRule(name="client", pattern="^[a-zA-Z0-9_-]{1,32}$")]
            ),
        },
    ]

    demo_clients = [
        {"name": "Faculdade XPTO", "slug": "faculdade-xpto", "domain": "xpto.example.com", "active": True},
        {"name": "Loja Alpha", "slug": "loja-alpha", "domain": "alpha.example.com", "active": True},
        {"name": "Clínica Beta", "slug": "clinica-beta", "domain": "beta.example.com", "active": True},
    ]

    with SessionLocal() as session:
        seed_default_token(session, settings.api_token)

        existing_scripts = {row.name for row in session.query(Script).all()}
        for payload in demo_scripts:
            script_path = settings.script_base_path / validate_filename(payload["filename"])
            if not script_path.is_file():
                _warn_missing_script(payload["filename"])
                if settings.environment == "production":
                    logger.warning("Production startup expects %s to exist before deployment.", script_path)
            if payload["name"] in existing_scripts:
                continue
            if not script_path.is_file():
                continue
            create_script(session, ScriptCreate(**payload))

        existing_clients = {row.slug for row in session.query(Client).all()}
        for payload in demo_clients:
            if payload["slug"] in existing_clients:
                continue
            client = create_client(session, ClientCreate(**payload))

        demo_matrix = {
            "faculdade-xpto": {"provisionar", "docker_status", "cleanup_logs"},
            "loja-alpha": {"docker_status", "backup"},
            "clinica-beta": {"cleanup_logs", "backup"},
        }
        scripts = {script.name: script for script in session.query(Script).all()}
        clients = {client.slug: client for client in session.query(Client).all()}
        for client_slug, allowed_scripts in demo_matrix.items():
            client = clients.get(client_slug)
            if client is None:
                continue
            for script_name in allowed_scripts:
                script = scripts.get(script_name)
                if script is None:
                    if settings.environment == "production":
                        logger.warning(
                            "Production seed missing expected script '%s' for client '%s'.",
                            script_name,
                            client_slug,
                        )
                    continue
                relation = session.query(ClientScript).filter(
                    ClientScript.client_id == client.id,
                    ClientScript.script_id == script.id,
                ).one_or_none()
                if relation is None:
                    set_client_script_active(session, client.id, script.id, True)


@app.on_event("startup")
def startup() -> None:
    _seed_scripts_and_clients()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=api_response(
            success=False,
            status="failed",
            message="Validation error",
            error_code="VALIDATION_ERROR",
            errors=exc.errors(),
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=api_response(
            success=False,
            status="failed",
            message=str(exc.detail),
            error_code=_http_error_code(exc.detail, exc.status_code),
        ),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content=api_response(
            success=False,
            status="failed",
            message="Database error",
            error_code="DATABASE_ERROR",
            errors=[{"detail": str(exc)}],
        ),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=api_response(
            success=False,
            status="failed",
            message="Unexpected error",
            error_code="INTERNAL_ERROR",
            errors=[{"detail": str(exc)}],
        ),
    )


app.include_router(health_router)
app.include_router(info_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(scripts_router, prefix=settings.api_prefix)
app.include_router(clients_router, prefix=settings.api_prefix)
app.include_router(logs_router, prefix=settings.api_prefix)
app.include_router(metrics_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
