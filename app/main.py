"""Aplicación FastAPI ampliada para la Práctica 4.3 (ADMINISTRACIÓN + CONTROL + MONITOREO)."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers existentes de 4.1 y 4.2
from app.api.vehicles import router as vehicles_router
from app.api.commands import router as commands_router
from app.api.state import router as state_router
from app.api.history import router as history_router
from app.api.movements import router as movements_router
from app.api.demos import router as demos_router
from app.api.demo_admin import router as demo_admin_router
from app.api.websocket import router as websocket_router
from app.api.websocket_manager import VehicleConnectionManager

# Nuevos Routers de la Práctica 4.3 (Administración, Roles, Catálogo y Sesiones)
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.models_admin import router as models_admin_router
from app.api.units_admin import router as units_admin_router
from app.api.clients_admin import router as clients_admin_router
from app.api.user_vehicles import router as user_vehicles_router
from app.api.guest_sessions import router as guest_sessions_router
from app.api.audit_admin import router as audit_admin_router

from app.core.config import Settings
from app.core.cors import get_allowed_origins
from app.core.database import create_database_engine
from app.repositories.vehicle_repository import VehicleRepository
from app.repositories.admin_repository import AdminRepository


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()
    application.state.settings = settings
    engine = create_database_engine(settings)
    application.state.engine = engine
    application.state.repository = VehicleRepository(engine)
    application.state.admin_repository = AdminRepository(engine)
    application.state.connections = VehicleConnectionManager()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Plataforma Comercial IoT (Práctica 4.3)",
    description="API REST y WSS para Administración, Control, Monitoreo y Demostraciones Comerciales IoT.",
    version="4.3.0",
    openapi_tags=[
        {"name": "Salud y Diagnóstico", "description": "Comprobación de API y disponibilidad de Amazon RDS."},
        {"name": "Autenticación", "description": "Inicio/cierre de sesión y perfil de usuario con RBAC."},
        {"name": "Modelos Comerciales", "description": "Catálogo comercial de productos y capacidades de hardware."},
        {"name": "Administración de Unidades", "description": "Inventario físico, asignaciones a compradores y soporte."},
        {"name": "Administración de Clientes", "description": "Gestión de compradores registrados."},
        {"name": "Mis Vehículos", "description": "Acceso exclusivo para que los compradores operen sus unidades."},
        {"name": "Invitados y Demostración Comercial", "description": "Reserva exclusiva temporal y pruebas de exhibición."},
        {"name": "Auditoría del Sistema", "description": "Registro de eventos administrativos y trazabilidad."},
        {"name": "Vehículos", "description": "Contrato de vehículos existente (4.1/4.2)."},
        {"name": "Comandos", "description": "Catálogo de comandos por vehículo."},
        {"name": "Estado", "description": "Estado actual reportado por la unidad física."},
        {"name": "Historial", "description": "Historial de los últimos diez movimientos."},
        {"name": "Movimientos", "description": "Envío de comandos de movimiento."},
        {"name": "Demos", "description": "Ejecución de secuencias DEMO."},
        {"name": "Movimientos de demo", "description": "Pasos individuales de secuencias."},
        {"name": "Tiempo real", "description": "Canal WebSocket WSS por vehículo."},
    ],
    lifespan=lifespan,
)

# CORS ampliado para admitir Authorization y métodos PUT/DELETE
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_allowed_origins()),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-API-Key"],
    allow_credentials=True,
)

# Inclusión de routers de 4.3
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(models_admin_router)
app.include_router(units_admin_router)
app.include_router(clients_admin_router)
app.include_router(user_vehicles_router)
app.include_router(guest_sessions_router)
app.include_router(audit_admin_router)

# Inclusión de routers existentes de 4.1 y 4.2
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
