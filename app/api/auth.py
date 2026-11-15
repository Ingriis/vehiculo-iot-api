"""Router de Autenticación, tokens de sesión y cierre de sesión."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_admin_repository, get_current_user
from app.core.security_jwt import create_access_token, verify_password
from app.repositories.admin_repository import AdminRepository

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: dict


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión")
async def login(
    payload: LoginRequest,
    request: Request,
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> LoginResponse:
    user = repo.get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        repo.log_audit(
            None, payload.username, "DESCONOCIDO", "LOGIN_FALLIDO", "auth:login",
            "Credenciales incorrectas", "FALLO", request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
        )

    if not user.get("activo", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta inactiva. Contacte al administrador.",
        )

    token_data = {
        "sub": user["id_usuario"],
        "username": user["username"],
        "rol": user["rol"],
        "nombre": user["nombre_completo"],
    }
    token = create_access_token(token_data)

    repo.log_audit(
        user["id_usuario"], user["username"], user["rol"], "LOGIN_EXITOSO", "auth:login",
        f"Inicio de sesión correcto con rol {user['rol']}", "EXITO",
        request.client.host if request.client else None
    )

    clean_user = {
        "id_usuario": user["id_usuario"],
        "username": user["username"],
        "email": user["email"],
        "nombre_completo": user["nombre_completo"],
        "rol": user["rol"],
    }
    return LoginResponse(access_token=token, token_type="Bearer", user=clean_user)


@router.post("/logout", summary="Cerrar sesión")
async def logout(
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    repo.log_audit(
        current_user["id_usuario"], current_user["username"], current_user["rol"],
        "LOGOUT", "auth:logout", "Cierre de sesión de usuario", "EXITO"
    )
    return {"status": "ok", "message": "Sesión cerrada correctamente."}


@router.get("/me", summary="Perfil de usuario actual")
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return {
        "id_usuario": current_user["id_usuario"],
        "username": current_user["username"],
        "email": current_user["email"],
        "nombre_completo": current_user["nombre_completo"],
        "rol": current_user["rol"],
    }
