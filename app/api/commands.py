"""Endpoints CRUD para los comandos asociados a un vehículo."""

from typing import Any

import pymysql
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services.command_service import CommandService
from app.core.security import require_api_key
from app.services.movement_service import CommandNotFoundError, VehicleNotFoundError

router = APIRouter(prefix="/vehicles/{vehicle_id}/commands", tags=["Comandos"])


class CommandCreate(BaseModel):
    nombre: str = Field(max_length=60)
    codigo: int
    descripcion: str | None = Field(default=None, max_length=255)


class CommandUpdate(CommandCreate):
    activo: bool


def _service(request: Request) -> CommandService:
    return CommandService(request.app.state.repository)


def _raise_not_found(exc: Exception) -> HTTPException:
    if isinstance(exc, VehicleNotFoundError):
        return HTTPException(status_code=404, detail="Vehículo no encontrado")
    return HTTPException(status_code=404, detail="Comando no encontrado para este vehículo")


def _raise_conflict(exc: pymysql.err.IntegrityError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Conflicto de integridad: el código/nombre puede estar duplicado o el comando está en uso.",
    )


@router.get("", summary="Listar comandos del vehículo", description="Stored Procedures: `sp_obtener_vehiculo` para validar el vehículo y `sp_obtener_comandos_vehiculo` para consultar el catálogo.")
async def list_commands(vehicle_id: int, request: Request) -> list[dict[str, Any]]:
    try:
        return await run_in_threadpool(_service(request).list_commands, vehicle_id)
    except VehicleNotFoundError as exc:
        raise _raise_not_found(exc) from exc


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear comando", description="Stored Procedures: `sp_obtener_vehiculo` para validar; `sp_crear_comando` para crear; `sp_obtener_comandos_vehiculo` para devolver el comando creado.", dependencies=[Depends(require_api_key)])
async def create_command(
    vehicle_id: int, payload: CommandCreate, request: Request
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).create_command,
            vehicle_id,
            payload.nombre,
            payload.codigo,
            payload.descripcion,
        )
    except VehicleNotFoundError as exc:
        raise _raise_not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _raise_conflict(exc) from exc


@router.put("/{command_id}", summary="Actualizar comando", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_comandos_vehiculo` para validar; `sp_actualizar_comando` para modificar; `sp_obtener_comandos_vehiculo` para devolver el resultado.", dependencies=[Depends(require_api_key)])
async def update_command(
    vehicle_id: int, command_id: int, payload: CommandUpdate, request: Request
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).update_command,
            vehicle_id,
            command_id,
            payload.nombre,
            payload.codigo,
            payload.descripcion,
            payload.activo,
        )
    except (VehicleNotFoundError, CommandNotFoundError) as exc:
        raise _raise_not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _raise_conflict(exc) from exc


@router.delete("/{command_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar comando", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_comandos_vehiculo` para validar; `sp_eliminar_comando` para eliminar.", dependencies=[Depends(require_api_key)])
async def delete_command(
    vehicle_id: int, command_id: int, request: Request
) -> Response:
    try:
        await run_in_threadpool(
            _service(request).delete_command, vehicle_id, command_id
        )
    except (VehicleNotFoundError, CommandNotFoundError) as exc:
        raise _raise_not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _raise_conflict(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
