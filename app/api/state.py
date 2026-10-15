"""Endpoint HTTP para consultar el estado actual del vehículo."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import VehicleNotFoundError
from app.services.vehicle_query_service import VehicleQueryService

router = APIRouter(prefix="/vehicles", tags=["Estado"])


@router.get("/{vehicle_id}/state", summary="Consultar estado actual", description="Stored Procedures: `sp_obtener_vehiculo` para validar el vehículo y `sp_obtener_estado` para leer el último estado.")
async def get_vehicle_state(
    vehicle_id: int, request: Request
) -> dict[str, Any] | None:
    """Devuelve el estado actual según sp_obtener_estado, o null si aún no existe."""
    service = VehicleQueryService(request.app.state.repository)
    try:
        return await run_in_threadpool(service.get_vehicle_state, vehicle_id)
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
