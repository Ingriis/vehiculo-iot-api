"""Endpoints administrativos para inventario de unidades físicas y asignación de clientes."""

from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_admin_repository, require_roles
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/admin/units", tags=["Administración de Unidades"])


class UnitCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    id_modelo: int
    numero_serie: str = Field(min_length=3, max_length=100)
    descripcion: str = Field(default="", max_length=255)
    microcontrolador: str = Field(default="ESP8266", max_length=50)
    estado_comercial: Literal["disponible", "vendido", "exhibicion", "inactivo"] = "disponible"


class UnitAssignment(BaseModel):
    propietario_id: int | None = None
    estado_comercial: Literal["disponible", "vendido", "exhibicion", "inactivo"]


class UnitSupportToggle(BaseModel):
    soporte_autorizado: bool


@router.get("", summary="Listar inventario completo de unidades físicas (Admin)")
async def list_units(
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> list[dict]:
    return repo.list_units()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Dar de alta unidad física (Admin)")
async def create_unit(
    payload: UnitCreate,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    model = repo.get_model(payload.id_modelo)
    if not model:
        raise HTTPException(status_code=404, detail="El modelo comercial especificado no existe.")

    try:
        unit_id = repo.create_unit(
            payload.nombre, payload.id_modelo, payload.numero_serie,
            payload.descripcion, payload.microcontrolador, payload.estado_comercial
        )
        repo.log_audit(
            current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
            "ALTA_UNIDAD", f"vehiculo:{unit_id}", f"Unidad serie {payload.numero_serie} dada de alta"
        )
        return {"id_vehiculo": unit_id, **payload.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"Error al registrar unidad: {str(exc)}")


@router.put("/{vehicle_id}/assignment", summary="Asignar comprador o cambiar estado comercial (Admin)")
async def assign_unit(
    vehicle_id: int,
    payload: UnitAssignment,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    unit = repo.get_unit_details(vehicle_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada.")

    propietario_anterior = unit.get("propietario_id")
    if payload.propietario_id:
        client = repo.get_user_by_id(payload.propietario_id)
        if not client or client.get("rol") != "USUARIO":
            raise HTTPException(status_code=400, detail="El ID del comprador especificado no es válido.")

    repo.update_unit_assignment(vehicle_id, payload.propietario_id, payload.estado_comercial)
    repo.log_audit(
        current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
        "ASIGNACION_UNIDAD", f"vehiculo:{vehicle_id}",
        f"Cambio propietario {propietario_anterior} -> {payload.propietario_id}, estado: {payload.estado_comercial}"
    )
    return {
        "id_vehiculo": vehicle_id,
        "propietario_anterior": propietario_anterior,
        "nuevo_propietario": payload.propietario_id,
        "estado_comercial": payload.estado_comercial,
        "mensaje": "Asignación actualizada con éxito."
    }


@router.put("/{vehicle_id}/support", summary="Habilitar/Deshabilitar sesión de soporte operativo")
async def toggle_support(
    vehicle_id: int,
    payload: UnitSupportToggle,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR", "USUARIO"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    unit = repo.get_unit_details(vehicle_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada.")

    repo.update_unit_support(vehicle_id, payload.soporte_autorizado)
    repo.log_audit(
        current_user["id_usuario"], current_user["username"], current_user["rol"],
        "SOPORTE_AUTORIZADO", f"vehiculo:{vehicle_id}",
        f"Soporte operativo establecido en {payload.soporte_autorizado}"
    )
    return {
        "id_vehiculo": vehicle_id,
        "soporte_autorizado": payload.soporte_autorizado
    }
