from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class MessageResponse(BaseModel):
    success: bool
    message: str
    data: object | None = None


class ParameterRule(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    pattern: str | None = None
    allowed_values: list[str] | None = None
    required: bool = True
    description: str | None = None

    @model_validator(mode="after")
    def validate_rule(self):
        if self.pattern is None and not self.allowed_values:
            raise ValueError("Cada parâmetro precisa ter pattern ou allowed_values.")
        if self.pattern is not None:
            if len(self.pattern) > 128:
                raise ValueError("Regex muito extensa.")
            if not self.pattern.startswith("^") or not self.pattern.endswith("$"):
                raise ValueError("Regex precisa ser ancorada com ^ e $.")
            forbidden_tokens = ("(?", "\\1", "\\2", "\\3", "\\g<", "(?P", "(?=", "(?!", "(?<=", "(?<!")
            if any(token in self.pattern for token in forbidden_tokens):
                raise ValueError("Regex contém construções não permitidas.")
            re.compile(self.pattern)
        if self.allowed_values is not None and not self.allowed_values:
            raise ValueError("allowed_values não pode ser vazio.")
        if self.allowed_values is not None:
            for value in self.allowed_values:
                if not isinstance(value, str) or not value or len(value) > 255 or re.search(r"[\x00-\x1f\x7f]", value):
                    raise ValueError("allowed_values contém item inválido.")
        return self


class AllowedParamsSchema(BaseModel):
    type: Literal["array"] = "array"
    items: list[ParameterRule]


class ScriptExecutionRequest(BaseModel):
    params: list[str] = Field(default_factory=list)


class TokenValueRequest(BaseModel):
    value: str


class HealthData(BaseModel):
    status: str
    service: str
    timestamp: datetime
