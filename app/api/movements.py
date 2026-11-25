"""Endpoints de movimientos individuales."""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import (
    CommandNotFoundError,
    InactiveCommandError,
    InactiveVehicleError,
    MovementService,
    VehicleNotFoundError,
)

router = APIRouter(prefix="/vehicles", tags=["Movimientos"])


class MovementRequest(BaseModel):
    command_id: int = Field(gt=0, description="ID del comando del vehículo")


class ControlStateRequest(BaseModel):
    forward: bool = False
    backward: bool = False
    left: bool = False
    right: bool = False
    lease_ms: int = Field(default=1600, ge=500, le=2500)


def _repository(request: Request) -> VehicleRepository:
    return request.app.state.repository


@router.post("/{vehicle_id}/movements", status_code=201, summary="Registrar movimiento", description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_comandos_vehiculo` y `sp_obtener_estado` para validar/leer; `sp_actualizar_estado` y `sp_registrar_historial` dentro de una transacción. Notifica por WebSocket después del commit.")
async def register_movement(
    vehicle_id: int, payload: MovementRequest, request: Request
) -> dict:
    """Valida, actualiza estado e historial, y notifica tras el commit."""
    service = MovementService(_repository(request))
    try:
        movement = await run_in_threadpool(
            service.register_movement, vehicle_id, payload.command_id
        )
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
    except CommandNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Comando no encontrado para este vehículo"
        ) from exc
    except InactiveVehicleError as exc:
        raise HTTPException(status_code=409, detail="El vehículo está inactivo") from exc
    except InactiveCommandError as exc:
        raise HTTPException(status_code=409, detail="El comando está inactivo") from exc

    # El servicio regresa después del commit; nunca emitir antes.
    await request.app.state.connections.broadcast(vehicle_id, {
        "type": "movement",
        "origin": "MANUAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **movement,
    })
    return movement


@router.post("/{vehicle_id}/control-state", summary="Actualizar señales independientes de control")
async def set_control_state(
    vehicle_id: int, payload: ControlStateRequest, request: Request
) -> dict:
    if payload.forward and payload.backward:
        raise HTTPException(status_code=422, detail="No se puede avanzar y retroceder al mismo tiempo.")
    if payload.left and payload.right:
        raise HTTPException(status_code=422, detail="No se puede girar a ambos lados al mismo tiempo.")
    if (payload.left or payload.right) and not (payload.forward or payload.backward):
        raise HTTPException(status_code=409, detail="Para girar, activa también avanzar o retroceder.")

    active_names = []
    if payload.forward:
        active_names.append("AVANZAR")
    if payload.backward:
        active_names.append("RETROCEDER")
    if payload.left:
        active_names.append("GIRAR_IZQUIERDA")
    if payload.right:
        active_names.append("GIRAR_DERECHA")

    service = MovementService(_repository(request))
    try:
        await run_in_threadpool(service.validate_control_state, vehicle_id, active_names)
    except VehicleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
    except InactiveVehicleError as exc:
        raise HTTPException(status_code=409, detail="El vehículo está inactivo") from exc
    except CommandNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Comando no encontrado para este vehículo") from exc
    except InactiveCommandError as exc:
        raise HTTPException(status_code=409, detail="Una señal solicitada está deshabilitada") from exc

    state = {
        "forward": payload.forward,
        "backward": payload.backward,
        "left": payload.left,
        "right": payload.right,
        "lease_ms": payload.lease_ms,
    }
    event = {
        "type": "control_state",
        "origin": "MANUAL",
        "id_vehiculo": vehicle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **state,
    }
    await request.app.state.connections.broadcast(vehicle_id, event)
    return state


