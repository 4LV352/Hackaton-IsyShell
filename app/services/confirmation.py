from fastapi import HTTPException, status


def require_confirmation(actual: str | None, expected: str) -> None:
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Confirmation required: {expected}.",
        )
