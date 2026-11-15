"""Endpoints de prueba temporal comercial y catálogo para Invitados."""

import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_admin_repository
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/guest", tags=["Invitados y Demostración Comercial"])

# Comandos seguros permitidos para invitados en exhibición
GUEST_ALLOWED_COMMAND_CODES = {1, 2, 3, 4, 8, 9, 11}  # AVANZAR, RETROCEDER, GIROS, LUCES, DETENER, SONIDO


class GuestSessionRequest(BaseModel):
    vehicle_id: int
    alias: str = Field(min_length=2, max_length=50)
    duracion_segundos: int = Field(default=180, ge=30, le=300)


@router.get("/catalog", summary="Catálogo público de modelos y disponibilidad de exhibición")
async def get_guest_catalog(
    repo: Annotated[AdminRepository, Depends(get_admin_repository)]
) -> list[dict]:
    # Exponer sólo unidades en exhibición, sin datos privados de clientes
    return repo.list_exhibition_units()


@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Solicitar sesión temporal de prueba en exhibición")
async def request_guest_session(
    payload: GuestSessionRequest,
    request: Request,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    unit = repo.get_unit_details(payload.vehicle_id)
    if not unit or unit.get("estado_comercial") != "exhibicion":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La unidad solicitada no existe o no está habilitada para demostraciones públicas de exhibición.",
        )

    # Verificar exclusividad: ¿Hay otra sesión activa vigente en esta unidad?
    active_session = repo.get_active_session(payload.vehicle_id)
    if active_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La unidad de exhibición está ocupada por '{active_session['alias_invitado']}'. Espere a que termine su turno ({active_session['segundos_restantes']} s restantes).",
        )

    token = secrets.token_hex(24)
    session_id = repo.create_guest_session(
        payload.vehicle_id, payload.alias, token, payload.duracion_segundos
    )

    repo.log_audit(
        None, payload.alias, "INVITADO", "RESERVA_DEMO_INICIADA",
        f"vehiculo:{payload.vehicle_id}",
        f"Sesión iniciada por {payload.alias} ({payload.duracion_segundos}s)",
        "EXITO", request.client.host if request.client else None
    )

    return {
        "id_sesion": session_id,
        "id_vehiculo": payload.vehicle_id,
        "token_sesion": token,
        "duracion_segundos": payload.duracion_segundos,
        "comandos_habilitados": list(GUEST_ALLOWED_COMMAND_CODES),
        "mensaje": "Sesión concedida con éxito. Controle la unidad antes de que expire el tiempo."
    }


@router.get("/sessions/{token}/status", summary="Consultar estado y tiempo restante de la sesión")
async def get_session_status(
    token: str,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    session = repo.get_session_by_token(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sesión de invitado no existe, ya expiró o fue finalizada.",
        )
    return {
        "id_sesion": session["id_sesion"],
        "id_vehiculo": session["id_vehiculo"],
        "alias": session["alias_invitado"],
        "segundos_restantes": max(0, session["segundos_restantes"]),
        "activa": session["activa"] and session["segundos_restantes"] > 0,
    }


@router.post("/sessions/{token}/release", summary="Liberar la unidad de exhibición (fin de prueba)")
async def release_guest_session(
    token: str,
    request: Request,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    session = repo.get_session_by_token(token)
    if not session:
        return {"mensaje": "La sesión ya no estaba activa."}

    repo.release_guest_session(session["id_sesion"], "USUARIO")

    # Detener de emergencia el vehículo físico vía manager
    connections = getattr(request.app.state, "connections", None)
    if connections:
        connections.cancel_demo(session["id_vehiculo"])

    repo.log_audit(
        None, session["alias_invitado"], "INVITADO", "RESERVA_DEMO_FINALIZADA",
        f"vehiculo:{session['id_vehiculo']}", "Sesión de invitado liberada voluntariamente",
        "EXITO", request.client.host if request.client else None
    )

    return {"mensaje": "Sesión de prueba finalizada y unidad liberada."}
