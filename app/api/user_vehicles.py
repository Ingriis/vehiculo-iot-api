"""Endpoints del módulo Mis Vehículos para el rol Usuario comprador."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_admin_repository, get_current_user, require_roles
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/user/vehicles", tags=["Mis Vehículos"])


@router.get("", summary="Listar vehículos asignados al comprador autenticado")
async def get_my_vehicles(
    current_user: Annotated[dict, Depends(require_roles(["USUARIO"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> list[dict]:
    units = repo.get_user_units(current_user["id_usuario"])
    return units
