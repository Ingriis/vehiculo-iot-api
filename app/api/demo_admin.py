"""Endpoints para administrar demos y pasos de sus secuencias."""

from typing import Any

import pymysql
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services.demo_admin_service import DemoAdminService, DemoMovementNotFoundError
from app.services.movement_service import CommandNotFoundError, VehicleNotFoundError
from app.services.vehicle_query_service import DemoNotFoundError

router = APIRouter(prefix="/vehicles/{vehicle_id}/demos")


class DemoCreate(BaseModel):
    nombre: str = Field(max_length=80)
    descripcion: str | None = Field(default=None, max_length=255)


class DemoUpdate(DemoCreate):
    activo: bool


class DemoMovementCreate(BaseModel):
    id_comando: int = Field(gt=0)
    orden: int = Field(gt=0)
    duracion_ms: int = Field(ge=0)
    pausa_ms: int = Field(ge=0)


class DemoMovementUpdate(DemoMovementCreate):
    pass


def _service(request: Request) -> DemoAdminService:
    return DemoAdminService(request.app.state.repository)


def _not_found(exc: Exception) -> HTTPException:
    if isinstance(exc, VehicleNotFoundError):
        message = "Vehículo no encontrado"
    elif isinstance(exc, DemoNotFoundError):
        message = "Demo no encontrada para este vehículo"
    elif isinstance(exc, CommandNotFoundError):
        message = "Comando no encontrado para este vehículo"
    else:
        message = "Movimiento no encontrado para esta demo"
    return HTTPException(status_code=404, detail=message)


def _conflict(exc: pymysql.err.IntegrityError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Conflicto de integridad; puede existir un orden duplicado.",
    )


@router.get("", tags=["Demos"], summary="Listar demos del vehículo", description="Stored Procedures: `sp_obtener_vehiculo` para validar y `sp_obtener_demos` para consultar.")
async def list_demos(vehicle_id: int, request: Request) -> list[dict[str, Any]]:
    try:
        return await run_in_threadpool(_service(request).list_demos, vehicle_id)
    except VehicleNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("", tags=["Demos"], status_code=status.HTTP_201_CREATED, summary="Crear demo", description="Stored Procedures: `sp_obtener_vehiculo` para validar; `sp_crear_demo` para crear; `sp_obtener_demos` para devolverla.")
async def create_demo(
    vehicle_id: int, payload: DemoCreate, request: Request
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).create_demo,
            vehicle_id,
            payload.nombre,
            payload.descripcion,
        )
    except VehicleNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{demo_id}/update", tags=["Demos"], summary="Actualizar demo", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_demos` para validar; `sp_actualizar_demo` para modificar; `sp_obtener_demos` para devolver el resultado.")
async def update_demo(
    vehicle_id: int, demo_id: int, payload: DemoUpdate, request: Request
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).update_demo,
            vehicle_id,
            demo_id,
            payload.nombre,
            payload.descripcion,
            payload.activo,
        )
    except (VehicleNotFoundError, DemoNotFoundError) as exc:
        raise _not_found(exc) from exc


@router.post("/{demo_id}", tags=["Demos"], status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar demo", description="Stored Procedures: `sp_obtener_vehiculo` y `sp_obtener_demos` para validar; `sp_eliminar_demo` para eliminar.")
async def delete_demo(vehicle_id: int, demo_id: int, request: Request) -> Response:
    try:
        await run_in_threadpool(_service(request).delete_demo, vehicle_id, demo_id)
    except (VehicleNotFoundError, DemoNotFoundError) as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{demo_id}/movements", tags=["Movimientos de demo"], summary="Listar pasos de una demo", description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_demos` para validar y `sp_obtener_movimientos_demo` para consultar pasos ordenados.")
async def list_demo_movements(
    vehicle_id: int, demo_id: int, request: Request
) -> list[dict[str, Any]]:
    try:
        return await run_in_threadpool(
            _service(request).list_movements, vehicle_id, demo_id
        )
    except (VehicleNotFoundError, DemoNotFoundError) as exc:
        raise _not_found(exc) from exc


@router.post(
    "/{demo_id}/movements",
    tags=["Movimientos de demo"],
    status_code=status.HTTP_201_CREATED,
    summary="Agregar paso a una demo",
    description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_demos` y `sp_obtener_comandos_vehiculo` para validar; `sp_agregar_movimiento_demo` para agregar; `sp_obtener_movimientos_demo` para devolver la lista actualizada.",
)
async def add_demo_movement(
    vehicle_id: int,
    demo_id: int,
    payload: DemoMovementCreate,
    request: Request,
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).add_movement,
            vehicle_id,
            demo_id,
            payload.id_comando,
            payload.orden,
            payload.duracion_ms,
            payload.pausa_ms,
        )
    except (VehicleNotFoundError, DemoNotFoundError, CommandNotFoundError) as exc:
        raise _not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _conflict(exc) from exc


@router.post(
    "/{demo_id}/movements/{movement_id}/update", tags=["Movimientos de demo"], summary="Actualizar paso de una demo", description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_demos`, `sp_obtener_movimientos_demo` y `sp_obtener_comandos_vehiculo` para validar; `sp_actualizar_movimiento_demo` para modificar; `sp_obtener_movimientos_demo` para devolver el resultado."
)
async def update_demo_movement(
    vehicle_id: int,
    demo_id: int,
    movement_id: int,
    payload: DemoMovementUpdate,
    request: Request,
) -> dict[str, Any]:
    try:
        return await run_in_threadpool(
            _service(request).update_movement,
            vehicle_id,
            demo_id,
            movement_id,
            payload.id_comando,
            payload.orden,
            payload.duracion_ms,
            payload.pausa_ms,
        )
    except (
        VehicleNotFoundError,
        DemoNotFoundError,
        DemoMovementNotFoundError,
        CommandNotFoundError,
    ) as exc:
        raise _not_found(exc) from exc
    except pymysql.err.IntegrityError as exc:
        raise _conflict(exc) from exc


@router.post(
    "/{demo_id}/movements/{movement_id}",
    tags=["Movimientos de demo"],
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar paso de una demo",
    description="Stored Procedures: `sp_obtener_vehiculo`, `sp_obtener_demos` y `sp_obtener_movimientos_demo` para validar; `sp_eliminar_movimiento_demo` para eliminar.",
)
async def delete_demo_movement(
    vehicle_id: int, demo_id: int, movement_id: int, request: Request
) -> Response:
    try:
        await run_in_threadpool(
            _service(request).delete_movement,
            vehicle_id,
            demo_id,
            movement_id,
        )
    except (
        VehicleNotFoundError,
        DemoNotFoundError,
        DemoMovementNotFoundError,
    ) as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


