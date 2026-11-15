"""Router para diagnóstico de salud de API y disponibilidad de Amazon RDS."""

import traceback
from typing import Annotated
from fastapi import APIRouter, Depends, Response, status

from app.core.dependencies import get_admin_repository
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/health", tags=["Salud y Diagnóstico"])


@router.get("", summary="Comprobar salud general de la API")
async def health_check() -> dict:
    return {"status": "available", "service": "FastAPI AWS", "version": "4.3"}


@router.get("/database", summary="Diagnóstico de conexión con Amazon RDS MySQL")
async def rds_health_check(
    response: Response,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    result = repo.check_rds_health()
    if result.get("status") != "available":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/debug", summary="Diagnóstico detallado de errores internos")
async def debug_check(
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    try:
        models = repo.list_models()
        user = repo.get_user_by_username("admin")
        catalog = repo.list_exhibition_units()
        return {
            "status": "success",
            "models_count": len(models),
            "admin_user_found": bool(user),
            "catalog_count": len(catalog),
        }
    except Exception as exc:
        return {
            "status": "exception",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
        }
