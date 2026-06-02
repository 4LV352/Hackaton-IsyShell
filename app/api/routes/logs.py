from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import api_response
from app.core.security import require_isy_token
from app.schemas.log import ExecutionLogRead
from app.services.execution_service import list_logs


router = APIRouter(prefix="/logs", tags=["Logs"], dependencies=[Depends(require_isy_token)])


@router.get("")
def get_execution_logs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    items, total = list_logs(session, limit=limit, offset=offset)
    data = {
        "items": [
            ExecutionLogRead(
                id=item.id,
                script_id=item.script_id,
                script_name=item.script_name,
                params=item.params,
                status=item.status,
                stdout=item.stdout,
                stderr=item.stderr,
                return_code=item.return_code,
                executed_at=item.executed_at,
            ).model_dump()
            for item in items
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }
    return api_response(success=True, message="Logs listados com sucesso.", data=data)
