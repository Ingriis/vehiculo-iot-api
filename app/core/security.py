"""Autenticación local por API key para operaciones de escritura y control."""

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def is_valid_api_key(expected: str | None, provided: str | None) -> bool:
    """Compara claves sin revelar cuál parte no coincidió."""
    return bool(expected and provided and secrets.compare_digest(expected, provided))


async def require_api_key(
    request: Request,
    provided: str | None = Depends(api_key_header),
) -> None:
    """Rechaza escrituras si falta la clave configurada o no coincide."""
    settings = getattr(request.app.state, "settings", None)
    expected = getattr(settings, "api_key", None)
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación de la API no está configurada.",
        )
    if not is_valid_api_key(expected, provided):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta una API key válida en el encabezado X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
