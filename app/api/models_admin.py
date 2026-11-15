"""Endpoints para catálogo comercial de modelos y definición de capacidades de hardware."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_admin_repository, get_current_user, require_roles
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/models", tags=["Modelos Comerciales"])


class ModelCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    codigo_modelo: str = Field(min_length=2, max_length=50)
    descripcion: str = Field(max_length=255)
    categoria: str = Field(default="Montacargas", max_length=50)
    imagen_url: str | None = None


class ModelUpdate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: str = Field(max_length=255)
    categoria: str = Field(max_length=50)
    activo: bool


@router.get("", summary="Listar catálogo de modelos comerciales")
async def list_models(
    repo: Annotated[AdminRepository, Depends(get_admin_repository)]
) -> list[dict]:
    return repo.list_models()


@router.get("/{model_id}", summary="Detalle de un modelo comercial")
async def get_model(
    model_id: int,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)]
) -> dict:
    model = repo.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado.")
    return model


@router.get("/{model_id}/capabilities", summary="Listar comandos/capacidades soportadas por el modelo")
async def get_model_capabilities(
    model_id: int,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)]
) -> list[dict]:
    return repo.list_model_capabilities(model_id)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear modelo comercial (Solo Admin)")
async def create_model(
    payload: ModelCreate,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    try:
        model_id = repo.create_model(
            payload.nombre, payload.codigo_modelo, payload.descripcion,
            payload.categoria, payload.imagen_url
        )
        repo.log_audit(
            current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
            "CREAR_MODELO", f"modelo:{model_id}", f"Modelo {payload.nombre} creado"
        )
        return {"id_modelo": model_id, **payload.model_dump()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo crear el modelo: {str(exc)}")


@router.put("/{model_id}", summary="Actualizar modelo comercial (Solo Admin)")
async def update_model(
    model_id: int,
    payload: ModelUpdate,
    current_user: Annotated[dict, Depends(require_roles(["ADMINISTRADOR"]))],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    model = repo.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado.")
    repo.update_model(model_id, payload.nombre, payload.descripcion, payload.categoria, payload.activo)
    repo.log_audit(
        current_user["id_usuario"], current_user["username"], "ADMINISTRADOR",
        "ACTUALIZAR_MODELO", f"modelo:{model_id}", f"Modelo {model_id} modificado"
    )
    return {"id_modelo": model_id, **payload.model_dump()}
