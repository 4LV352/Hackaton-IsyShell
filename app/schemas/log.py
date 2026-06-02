from datetime import datetime

from pydantic import BaseModel


class ExecutionLogRead(BaseModel):
    id: int
    script_id: int
    script_name: str
    params: list[str]
    status: str
    stdout: str
    stderr: str
    return_code: int
    executed_at: datetime
