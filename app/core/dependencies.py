"""Dependencias de FastAPI para RBAC, validación de propiedad de recursos (anti-BOLA/IDOR) y autenticación."""

from typing import Annotated, Sequence
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security_jwt import decode_access_token
from app.repositories.admin_repository import AdminRepository

security_bearer = HTTPBearer(auto_error=False)


def get_admin_repository(request: Request) -> AdminRepository:
    """Instancia o reutiliza el repositorio administrativo."""
    if not hasattr(request.app.state, "admin_repository"):
        request.app.state.admin_repository = AdminRepository(request.app.state.engine)
    return request.app.state.admin_repository


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
) -> dict:
    """Extrae y valida el token Bearer del encabezado Authorization."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autenticación. Inicie sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado. Vuelva a iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = repo.get_user_by_id(payload["sub"])
    if not user or not user.get("activo", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La cuenta de usuario está inactiva o no existe.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(allowed_roles: Sequence[str]):
    """Genera una dependencia que valida que el usuario posea uno de los roles autorizados."""
    async def role_checker(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_role = current_user.get("rol", "").upper()
        if user_role not in [r.upper() for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: se requiere uno de los roles [{', '.join(allowed_roles)}]. Su rol es '{user_role}'.",
            )
        return current_user
    return role_checker


async def verify_vehicle_authorization(
    vehicle_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: Annotated[AdminRepository, Depends(get_admin_repository)],
    require_write: bool = False,
) -> dict:
    """
    Verifica que el usuario tenga autorización sobre el vehículo solicitado (anti-BOLA/IDOR).
    - USUARIO: sólo puede operar/consultar si es el propietario asignado.
    - ADMINISTRADOR: puede ver inventario; pero si require_write=True (operar movimientos),
      requiere que 'soporte_autorizado' sea verdadero si la unidad ya está vendida.
    """
    unit = repo.get_unit_details(vehicle_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehículo con ID {vehicle_id} no encontrado.",
        )

    user_role = current_user.get("rol", "").upper()
    user_id = current_user["id_usuario"]

    if user_role == "ADMINISTRADOR":
        if require_write and unit.get("estado_comercial") == "vendido":
            if not unit.get("soporte_autorizado", False):
                repo.log_audit(
                    user_id, current_user["username"], user_role,
                    "INTENTO_CONTROL_SIN_SOPORTE", f"vehiculo:{vehicle_id}",
                    "El administrador intentó operar una unidad vendida sin sesión de soporte autorizada.",
                    "DENEGADO"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Operación no permitida: la unidad está vendida y no tiene activa una sesión de soporte autorizada por el cliente.",
                )
        return unit

    if user_role == "USUARIO":
        if unit.get("propietario_id") != user_id:
            repo.log_audit(
                user_id, current_user["username"], user_role,
                "ACCESO_CRUZADO_BOLA", f"vehiculo:{vehicle_id}",
                f"Usuario {current_user['username']} intentó acceder al vehículo {vehicle_id} perteneciente a otro propietario.",
                "DENEGADO"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso prohibido: este vehículo no está asignado a su cuenta.",
            )
        return unit

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Su rol no tiene autorización para operar vehículos privados.",
    )
