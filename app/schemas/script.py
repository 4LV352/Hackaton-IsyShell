from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.common import AllowedParamsSchema


class ScriptCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    allowed_params_schema: AllowedParamsSchema
    active: bool = True


class ScriptUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    filename: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    allowed_params_schema: AllowedParamsSchema | None = None


class ScriptRead(BaseModel):
    id: int
    name: str
    filename: str
    description: str | None
    allowed_params_schema: dict
    active: bool
    created_at: datetime
    updated_at: datetime


class ScriptExecuteResult(BaseModel):
    script_id: int
    script_name: str
    params: list[str]
    status: str
    stdout: str
    stderr: str
    return_code: int
    executed_at: datetime
