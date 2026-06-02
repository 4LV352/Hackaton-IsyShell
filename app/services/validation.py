from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import HTTPException, status


FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+\.sh$")
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def ensure_safe_filename(filename: str) -> str:
    if not filename or not FILENAME_PATTERN.fullmatch(filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nome de arquivo inválido. Use apenas um .sh sem caminhos absolutos ou relativos.",
        )
    return filename


def ensure_safe_script_path(script_dir: Path, filename: str) -> Path:
    safe_filename = ensure_safe_filename(filename)
    candidate = (script_dir / safe_filename).resolve()
    base_dir = script_dir.resolve()
    try:
        candidate.relative_to(base_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho do script fora do diretório permitido.",
        ) from exc
    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script não encontrado no diretório permitido.",
        )
    return candidate


def validate_token_value(value: str) -> str:
    if not value or len(value) < 8 or len(value) > 256 or CONTROL_CHARS_PATTERN.search(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Token inválido. O valor precisa ter entre 8 e 256 caracteres e não pode conter controles.",
        )
    return value


def validate_parameter_value(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 255 or CONTROL_CHARS_PATTERN.search(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parâmetro inválido.",
        )
    return value


def validate_regex_pattern(pattern: str) -> str:
    if not pattern or len(pattern) > 128:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Regex inválida ou extensa demais.",
        )
    if not pattern.startswith("^") or not pattern.endswith("$"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Regex precisa ser ancorada com ^ e $.",
        )
    forbidden_tokens = ("(?", "\\1", "\\2", "\\3", "\\g<", "(?P", "(?=", "(?!", "(?<=", "(?<!")
    if any(token in pattern for token in forbidden_tokens):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Regex contém construções não permitidas.",
        )
    try:
        re.compile(pattern)
    except re.error as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Regex inválida.",
        ) from exc
    return pattern
