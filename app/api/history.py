"""Endpoint HTTP para consultar los movimientos recientes del vehículo."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.services.movement_service import VehicleNotFoundError
from app.services.vehicle_query_service import VehicleQueryService

router = APIRouter(prefix="/vehicles", tags=["Historial"])


@router.get("/{vehicle_id}/history", summary="Consultar los diez movimientos recientes", description="Stored Procedures: `sp_obtener_vehiculo` para validar y `sp_obtener_historial` para consultar. La API limita la respuesta a diez registros y no modifica datos.")
async def get_history(vehicle_id: int, request: Request) -> list[dict[str, Any]]:
    """Devuelve hasta diez registros, del más reciente al más antiguo."""
    service = VehicleQueryService(request.app.state.repository)
    try:
        return await run_in_threadpool(service.get_history, vehicle_id)
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
