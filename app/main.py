"""Aplicación FastAPI; su servidor integrado escucha solo en loopback."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.vehicles import router as vehicles_router
from app.api.commands import router as commands_router
from app.api.state import router as state_router
from app.api.history import router as history_router
from app.api.movements import router as movements_router
from app.api.demos import router as demos_router
from app.api.demo_admin import router as demo_admin_router
from app.api.websocket import router as websocket_router
from app.api.websocket_manager import VehicleConnectionManager
from app.core.config import Settings
from app.core.database import create_database_engine
from app.repositories.vehicle_repository import VehicleRepository


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()
    application.state.settings = settings
    engine = create_database_engine(settings)
    application.state.engine = engine
    application.state.repository = VehicleRepository(engine)
    application.state.connections = VehicleConnectionManager()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="API IoT de vehículos",
    description="API local para controlar y consultar movimientos de vehículos IoT.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Vehículos", "description": "Administración de vehículos."},
        {"name": "Comandos", "description": "Comandos asociados a vehículos."},
        {"name": "Estado", "description": "Estado actual y conexión del vehículo."},
        {"name": "Historial", "description": "Hasta diez comandos recientes, con su origen."},
        {"name": "Movimientos", "description": "Registro de movimientos manuales."},
        {"name": "Demos", "description": "Administración y ejecución de demos."},
        {"name": "Movimientos de demo", "description": "Pasos que componen cada demo."},
    ],
    lifespan=lifespan,
)
app.include_router(vehicles_router)
app.include_router(commands_router)
app.include_router(state_router)
app.include_router(history_router)
app.include_router(movements_router)
app.include_router(demos_router)
app.include_router(demo_admin_router)
app.include_router(websocket_router)


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
