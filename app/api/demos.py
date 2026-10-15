"""Endpoint para reproducir una DEMO guardada en RDS."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.repositories.vehicle_repository import VehicleRepository
from app.core.security import require_api_key
from app.services.movement_service import VehicleNotFoundError
from app.services.vehicle_query_service import (
    DemoNotFoundError,
    InactiveDemoError,
    InactiveCommandInDemoError,
    InactiveVehicleError,
    VehicleQueryService,
)

router = APIRouter(prefix="/vehicles", tags=["Demos"])


class DemoRunResponse(BaseModel):
    vehicle_id: int
    demo_id: int
    status: str
    movements_transmitted: int
    detail: str


async def _wait_or_cancel(cancellation: asyncio.Event, milliseconds: int) -> bool:
    """Espera la duración indicada y devuelve True si se pidió cancelar."""
    if cancellation.is_set():
        return True
    if milliseconds <= 0:
        return False
    try:
        await asyncio.wait_for(cancellation.wait(), timeout=milliseconds / 1000)
        return True
    except asyncio.TimeoutError:
        return False


@router.post(
    "/{vehicle_id}/demos/{demo_id}/run",
    response_model=DemoRunResponse,
    summary="Ejecutar demo",
    description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_demos`, `sp_obtener_movimientos_demo` y `sp_obtener_comandos_vehiculo` para validar/cargar la secuencia; `sp_obtener_estado` y `sp_actualizar_estado` por paso. No llama a `sp_registrar_historial`.",
    dependencies=[Depends(require_api_key)],
)
async def run_demo(
    vehicle_id: int, demo_id: int, request: Request
) -> DemoRunResponse:
    """Transmite una secuencia en orden y actualiza el estado sin tocar historial."""
    manager = request.app.state.connections
    cancellation = manager.begin_demo(vehicle_id)
    if cancellation is None:
        raise HTTPException(status_code=409, detail="Ya hay una demo ejecutándose para este vehículo")

    repository: VehicleRepository = request.app.state.repository
    query_service = VehicleQueryService(repository)
    transmitted = 0
    try:
        try:
            sequence = await run_in_threadpool(
                query_service.get_demo_sequence, vehicle_id, demo_id
            )
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado") from exc
        except DemoNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail="Demo no encontrada para este vehículo"
            ) from exc
        except InactiveVehicleError as exc:
            raise HTTPException(status_code=409, detail="El vehículo está inactivo") from exc
        except InactiveDemoError as exc:
            raise HTTPException(status_code=409, detail="La demo está inactiva") from exc
        except InactiveCommandInDemoError as exc:
            raise HTTPException(
                status_code=409, detail="La demo contiene un comando inactivo"
            ) from exc

        await manager.broadcast(vehicle_id, {
            "type": "demo_started",
            "id_vehiculo": vehicle_id,
            "id_demo": demo_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        for movement in sequence:
            if cancellation.is_set():
                break
            duration_ms = int(movement["duracion_ms"])
            pause_ms = int(movement["pausa_ms"])
            # Commit del estado antes de notificar; este flujo no registra historial.
            await run_in_threadpool(
                query_service.update_demo_state,
                vehicle_id,
                int(movement["id_comando"]),
            )
            event: dict[str, Any] = {
                "type": "movement",
                "origin": "DEMO",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "id_vehiculo": vehicle_id,
                "id_demo": demo_id,
                "id_demo_movimiento": movement["id_demo_movimiento"],
                "orden": movement["orden"],
                "id_comando": movement["id_comando"],
                "comando": movement["comando"],
                "codigo": movement["codigo"],
                "duracion_ms": duration_ms,
                "pausa_ms": pause_ms,
            }
            await manager.broadcast(vehicle_id, event)
            transmitted += 1
            if await _wait_or_cancel(cancellation, duration_ms):
                break
            if await _wait_or_cancel(cancellation, pause_ms):
                break

        cancelled = cancellation.is_set()
        status = "cancelled" if cancelled else "completed"
        await manager.broadcast(vehicle_id, {
            "type": "demo_cancelled" if cancelled else "demo_finished",
            "id_vehiculo": vehicle_id,
            "id_demo": demo_id,
            "movements_transmitted": transmitted,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return DemoRunResponse(
            vehicle_id=vehicle_id,
            demo_id=demo_id,
            status=status,
            movements_transmitted=transmitted,
            detail="Demo cancelada." if cancelled else "Demo transmitida por WebSocket.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        await manager.broadcast(vehicle_id, {
            "type": "demo_error",
            "id_vehiculo": vehicle_id,
            "id_demo": demo_id,
            "detail": "Error al ejecutar la demo.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(status_code=500, detail="Error al ejecutar la demo") from exc
    finally:
        manager.finish_demo(vehicle_id, cancellation)
