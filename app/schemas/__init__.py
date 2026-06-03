from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _reject_controls(value: str) -> str:
    if not value or len(value) > 255 or re.search(r"[\x00-\x1f\x7f]", value):
        raise ValueError("Invalid value.")
    return value


class ParameterRule(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    pattern: str | None = None
    allowed_values: list[str] | None = None
    required: bool = True
    description: str | None = None

    @model_validator(mode="after")
    def validate_rule(self):
        if self.pattern is None and not self.allowed_values:
            raise ValueError("Each parameter needs a pattern or allowed_values.")
        if self.pattern is not None:
            if len(self.pattern) > 128:
                raise ValueError("Regex too long.")
            if not self.pattern.startswith("^") or not self.pattern.endswith("$"):
                raise ValueError("Regex must be anchored.")
            forbidden_tokens = ("(?", "\\1", "\\2", "\\3", "\\g<", "(?P", "(?=", "(?!", "(?<=", "(?<!")
            if any(token in self.pattern for token in forbidden_tokens):
                raise ValueError("Forbidden regex tokens.")
            re.compile(self.pattern)
        if self.allowed_values is not None:
            if not self.allowed_values:
                raise ValueError("allowed_values cannot be empty.")
            for item in self.allowed_values:
                _reject_controls(item)
        return self


class AllowedParamsSchema(BaseModel):
    type: Literal["array"] = "array"
    items: list[ParameterRule]


class StandardResponse(BaseModel):
    success: bool
    status: str
    message: str | None = None
    data: object | None = None
    errors: object | None = None


class ScriptCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "provisionar",
                "filename": "provisionar.sh",
                "description": "Provisionamento simulado",
                "allowed_params_schema": {
                    "type": "array",
                    "items": [
                        {"name": "client", "pattern": "^[a-zA-Z0-9_-]{1,32}$"},
                        {"name": "domain", "pattern": "^[a-zA-Z0-9.-]{1,253}$"},
                        {"name": "port", "pattern": "^[0-9]{2,5}$"},
                    ],
                },
                "active": True,
            }
        }
    )

    name: Annotated[str, Field(min_length=1, max_length=120)]
    filename: Annotated[str, Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.-]+\.sh$")]
    description: str | None = None
    allowed_params_schema: AllowedParamsSchema
    active: bool = True


class ScriptUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    filename: Annotated[str, Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.-]+\.sh$")] | None = None
    description: str | None = None
    allowed_params_schema: AllowedParamsSchema | None = None
    active: bool | None = None


class ScriptRead(BaseModel):
    id: int
    name: str
    filename: str
    description: str | None
    allowed_params_schema: dict
    active: bool
    created_at: datetime
    updated_at: datetime


class ScriptExecutionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": 1,
                "params": ["cliente01", "cliente01.isy.one", "8155"],
                "confirm": "EXECUTAR",
            }
        }
    )

    client_id: int
    params: list[str] = Field(default_factory=list)
    confirm: str


class ScriptExecutionResult(BaseModel):
    success: bool
    status: str
    script: str
    client: str
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int
    log_id: int
    message: str | None = None


class ClientCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Novo Cliente",
                "domain": "novo.exemplo.com",
                "active": True,
            }
        }
    )

    name: Annotated[str, Field(min_length=1, max_length=160)]
    slug: Annotated[str | None, Field(default=None, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] = None
    domain: Annotated[str, Field(min_length=1, max_length=255)]
    active: bool = True


class ClientUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    slug: Annotated[str, Field(min_length=1, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")] | None = None
    domain: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    active: bool | None = None


class ClientRead(BaseModel):
    id: int
    name: str
    slug: str
    domain: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ExecutionLogRead(BaseModel):
    id: int
    client_id: int
    script_id: int
    client_name: str
    script_name: str
    params: list[str]
    status: str
    stdout: str
    stderr: str
    return_code: int
    duration_ms: int
    requester_ip: str
    token_fingerprint: str
    executed_at: datetime


class TokenPayload(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"value": "novo-token-seguro"}})

    value: str

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value or len(value) < 8 or len(value) > 256 or re.search(r"[\x00-\x1f\x7f]", value):
            raise ValueError("Invalid token.")
        return value


class ConfirmationPayload(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"confirm": "CONFIRMACAO_ESPERADA"}})

    confirm: Annotated[str, Field(min_length=1, max_length=64)]


class TokenRegenerateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"confirm": "REGENERAR_TOKEN"}})

    confirm: Literal["REGENERAR_TOKEN"]


class MetricsRead(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_duration_ms: float
    executions_today: int
    last_script_executed: dict | None
    active_clients: int
    active_scripts: int
