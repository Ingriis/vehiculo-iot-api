"""Router para diagnóstico de salud de API y disponibilidad de Amazon RDS."""

from typing import Annotated
from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_admin_repository
from app.repositories.admin_repository import AdminRepository

router = APIRouter(tags=["Salud y Diagnóstico"])


@router.get("/health", summary="Comprobar salud general de la API")
async def health_check() -> dict:
    return {"status": "available", "service": "FastAPI AWS", "version": "4.3"}


@router.get("/health/database", summary="Diagnóstico de conexión con Amazon RDS MySQL")
async def rds_health_check(
    response: Response,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    result = repo.check_rds_health()
    if result.get("status") != "available":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
