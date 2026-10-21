"""Endpoints CRUD para vehículos."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import VehicleNotFoundError
from app.services.vehicle_service import VehicleService

router = APIRouter(prefix="/vehicles", tags=["Vehículos"])


class VehicleCreate(BaseModel):
    nombre: str = Field(max_length=80)
    modelo: str = Field(max_length=80)
    descripcion: str = Field(max_length=255)
    microcontrolador: str = Field(max_length=50)


class VehicleUpdate(VehicleCreate):
    activo: bool


def _service(request: Request) -> VehicleService:
    return VehicleService(request.app.state.repository)


@router.get("", summary="Listar vehículos", description="Stored Procedures: `sp_obtener_vehiculos`.")
async def list_vehicles(request: Request) -> list[dict[str, Any]]:
    return await run_in_threadpool(_service(request).list_vehicles)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear vehículo", description="Stored Procedures: `sp_crear_vehiculo` y `sp_obtener_vehiculo` para devolver el recurso creado.")
async def create_vehicle(payload: VehicleCreate, request: Request) -> dict[str, Any]:
    return await run_in_threadpool(
        _service(request).create_vehicle,
        payload.nombre,
        payload.modelo,
        payload.descripcion,
        payload.microcontrolador,
    )


@router.get("/{vehicle_id}", summary="Consultar vehículo", description="Stored Procedures: `sp_obtener_vehiculo`.")
async def get_vehicle(vehicle_id: int, request: Request) -> dict[str, Any]:
    try:
        return await run_in_threadpool(_service(request).get_vehicle, vehicle_id)
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc


@router.post("/{vehicle_id}/update", summary="Actualizar vehículo", description="Stored Procedures: `sp_obtener_vehiculo` para validar y leer, `sp_actualizar_vehiculo` para modificar y `sp_obtener_vehiculo` para devolver el resultado.")
async def update_vehicle(
    vehicle_id: int, payload: VehicleUpdate, request: Request
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).update_vehicle,
            vehicle_id,
            payload.nombre,
            payload.modelo,
            payload.descripcion,
            payload.microcontrolador,
            payload.activo,
        )
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc


@router.post("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar vehículo", description="Stored Procedures: `sp_obtener_vehiculo` para validar y `sp_eliminar_vehiculo` para eliminar.")
async def delete_vehicle(vehicle_id: int, request: Request) -> Response:
    try:
        await run_in_threadpool(_service(request).delete_vehicle, vehicle_id)
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
