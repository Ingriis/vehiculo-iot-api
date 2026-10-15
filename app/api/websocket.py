"""Endpoint WebSocket con estado inicial y actualizaciones por vehículo."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool

from app.services.movement_service import VehicleNotFoundError
from app.services.vehicle_query_service import VehicleQueryService
from app.core.security import is_valid_api_key

router = APIRouter(tags=["Tiempo real"])


@router.websocket("/ws/vehicles/{vehicle_id}")
async def vehicle_updates(websocket: WebSocket, vehicle_id: int) -> None:
    manager = websocket.app.state.connections
    await manager.connect(vehicle_id, websocket)
    try:
        repository = websocket.app.state.repository
        state = await run_in_threadpool(
            VehicleQueryService(repository).get_vehicle_state, vehicle_id
        )
        await websocket.send_json(jsonable_encoder({"type": "initial_state", "state": state}))
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Envía JSON válido."})
                continue
            if isinstance(message, dict) and message.get("action") == "cancel_demo":
                settings = getattr(websocket.app.state, "settings", None)
                expected_key = getattr(settings, "api_key", None)
                provided_key = websocket.headers.get("x-api-key")
                if not is_valid_api_key(expected_key, provided_key):
                    await websocket.send_json({
                        "type": "authorization_error",
                        "detail": "Se requiere una API key válida para cancelar una demo.",
                    })
                    continue
                cancelled = manager.cancel_demo(vehicle_id)
                await websocket.send_json({
                    "type": "demo_cancel_requested" if cancelled else "demo_not_running",
                    "id_vehiculo": vehicle_id,
                })
    except VehicleNotFoundError:
        await websocket.send_json({"type": "error", "detail": "Vehículo no encontrado"})
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(vehicle_id, websocket)
