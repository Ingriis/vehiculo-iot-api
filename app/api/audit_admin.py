"""Endpoints de consulta de bitácora de auditoría para el Administrador."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_admin_repository, require_roles
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/admin/audit-logs", tags=["Auditoría del Sistema"])


@router.get("", summary="Consultar bitácora de auditoría (Admin)")
async def get_audit_logs(
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return repo.list_audit_logs(limit)
