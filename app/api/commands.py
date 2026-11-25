"""Endpoints CRUD para los comandos asociados a un vehículo."""

from typing import Annotated, Any

import pymysql
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_admin_repository, require_roles, verify_vehicle_authorization
from app.repositories.admin_repository import AdminRepository
from app.services.command_service import CommandService
from app.services.movement_service import CommandNotFoundError, VehicleNotFoundError

router = APIRouter(prefix="/vehicles/{vehicle_id}/commands", tags=["Comandos"])


class CommandCreate(BaseModel):
    nombre: str = Field(max_length=60)
    codigo: int
    descripcion: str | None = Field(default=None, max_length=255)


class CommandUpdate(CommandCreate):
    activo: bool


class CommandEnabled(BaseModel):
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


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear comando", description="Stored Procedures: `sp_obtener_vehiculo` para validar; `sp_crear_comando` para crear; `sp_obtener_comandos_vehiculo` para devolver el comando creado.")
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


@router.post("/{command_id}/update", summary="Actualizar comando", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_comandos_vehiculo` para validar; `sp_actualizar_comando` para modificar; `sp_obtener_comandos_vehiculo` para devolver el resultado.")
async def update_command(
    vehicle_id: int,
    command_id: int,
    payload: CommandUpdate,
    request: Request,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
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


@router.post("/{command_id}/enabled", summary="Activar o desactivar un comando propio")
async def set_command_enabled(
    vehicle_id: int,
    command_id: int,
    payload: CommandEnabled,
    request: Request,
    current_user: Annotated[dict, Depends(require_roles(["USUARIO"]))],
    admin_repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict[str, Any]:
    """Permite activar o desactivar un comando; el comprador sólo puede cambiar su unidad asignada."""
    await verify_vehicle_authorization(vehicle_id, current_user, admin_repo)
    service = _service(request)
    try:
        commands = await run_in_threadpool(service.list_commands, vehicle_id)
        command = next((item for item in commands if int(item["id_comando"]) == command_id), None)
        if command is None:
            raise CommandNotFoundError(command_id)
        updated = await run_in_threadpool(
            service.update_command,
            vehicle_id,
            command_id,
            command["nombre"],
            int(command["codigo"]),
            command.get("descripcion"),
            payload.activo,
        )
        await run_in_threadpool(
            admin_repo.log_audit,
            current_user["id_usuario"],
            current_user["username"],
            current_user["rol"],
            "CAMBIAR_ESTADO_COMANDO",
            f"vehiculo:{vehicle_id}/comando:{command_id}",
            f"Comando {command['nombre']} establecido en {'activo' if payload.activo else 'inactivo'} por el propietario.",
        )
        return updated
    except (VehicleNotFoundError, CommandNotFoundError) as exc:
        raise _raise_not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _raise_conflict(exc) from exc


@router.post("/{command_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar comando", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_comandos_vehiculo` para validar; `sp_eliminar_comando` para eliminar.")
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
