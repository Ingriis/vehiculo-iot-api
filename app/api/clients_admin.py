"""Endpoints para administración de clientes compradores."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.dependencies import get_admin_repository, require_roles
from app.core.security_jwt import hash_password
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/admin/clients", tags=["Administración de Clientes"])


class ClientCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=120)
    password: str = Field(min_length=6)
    nombre_completo: str = Field(min_length=2, max_length=120)


@router.get("", summary="Listar compradores (Admin)")
async def list_clients(
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> list[dict]:
    return repo.list_clients()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Registrar nuevo comprador (Admin)")
async def create_client(
    payload: ClientCreate,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    existing_user = repo.get_user_by_username(payload.username)
    if existing_user:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado.")

    password_hash = hash_password(payload.password)
    try:
        user_id = repo.create_user(
            payload.username, payload.email, password_hash, payload.nombre_completo, "USUARIO"
        )
        repo.log_audit(
            current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
            "ALTA_CLIENTE", f"usuario:{user_id}", f"Cliente {payload.username} creado"
        )
        return {
            "id_usuario": user_id,
            "username": payload.username,
            "email": payload.email,
            "nombre_completo": payload.nombre_completo,
            "rol": "USUARIO"
        }
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo crear el comprador: {str(exc)}")


class ClientUpdate(BaseModel):
    email: str = Field(max_length=120)
    nombre_completo: str = Field(min_length=2, max_length=120)
    activo: bool


@router.put("/{client_id}", summary="Editar o desactivar un cliente comprador (Admin)")
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    client = repo.get_user_by_id(client_id)
    if not client or client.get("rol") != "USUARIO":
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")

    try:
        repo.update_client(client_id, payload.nombre_completo, payload.email, payload.activo)
        action = "ACTUALIZAR_CLIENTE" if payload.activo else "DESACTIVAR_CLIENTE"
        repo.log_audit(
            current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
            action, f"usuario:{client_id}",
            f"Cliente {client['username']} actualizado; activo={payload.activo}",
        )
        return {
            "id_usuario": client_id,
            "username": client["username"],
            "email": payload.email,
            "nombre_completo": payload.nombre_completo,
            "rol": "USUARIO",
            "activo": payload.activo,
        }
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo actualizar el cliente: {str(exc)}")
