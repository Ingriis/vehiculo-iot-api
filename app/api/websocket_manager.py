"""Administrador de conexiones WebSocket por vehículo."""

import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class VehicleConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}
        self._demo_cancellations: dict[int, asyncio.Event] = {}

    def begin_demo(self, vehicle_id: int) -> asyncio.Event | None:
        """Registra una ejecución exclusiva por vehículo; None si ya hay otra."""
        if vehicle_id in self._demo_cancellations:
            return None
        cancellation = asyncio.Event()
        self._demo_cancellations[vehicle_id] = cancellation
        return cancellation

    def cancel_demo(self, vehicle_id: int) -> bool:
        cancellation = self._demo_cancellations.get(vehicle_id)
        if cancellation is None:
            return False
        cancellation.set()
        return True

    def finish_demo(self, vehicle_id: int, cancellation: asyncio.Event) -> None:
        if self._demo_cancellations.get(vehicle_id) is cancellation:
            self._demo_cancellations.pop(vehicle_id, None)

    async def connect(self, vehicle_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(vehicle_id, []).append(websocket)

    def disconnect(self, vehicle_id: int, websocket: WebSocket) -> None:
        subscribers = self._connections.get(vehicle_id, [])
        if websocket in subscribers:
            subscribers.remove(websocket)
        if not subscribers:
            self._connections.pop(vehicle_id, None)

    async def broadcast(self, vehicle_id: int, message: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in tuple(self._connections.get(vehicle_id, [])):
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    stale.append(websocket)
            except (RuntimeError, OSError, WebSocketDisconnect):
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(vehicle_id, websocket)
