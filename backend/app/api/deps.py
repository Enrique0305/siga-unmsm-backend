from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class CurrentUser:
    """
    Representa al usuario autenticado a partir del payload del JWT — no se
    vuelve a consultar la tabla `usuario` en cada request (ver
    core/security.py: create_access_token incluye rol y almacenes).
    """

    usuario_id: int
    rol: str
    almacenes: list[int]
    acceso_todos_almacenes: bool

    def tiene_acceso_almacen(self, almacen_id: int) -> bool:
        return self.acceso_todos_almacenes or almacen_id in self.almacenes


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o expiradas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        usuario_id=int(payload["sub"]),
        rol=payload["rol"],
        almacenes=payload.get("almacenes", []),
        acceso_todos_almacenes=payload.get("acceso_todos_almacenes", False),
    )


def require_roles(*roles_permitidos: str):
    """
    Uso: `current = Depends(require_roles("ADMIN", "LOGISTICA_CENTRAL"))`
    """

    async def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{current.rol}' no tiene permiso para esta operación",
            )
        return current

    return _checker


def require_almacen_access(almacen_id_param: str = "almacen_id"):
    """
    Dependency factory que valida RN-20 (alcance por almacén) leyendo el
    almacen_id desde los path params del endpoint. Uso:

        @router.get("/almacenes/{almacen_id}/stock")
        async def listar_stock(
            almacen_id: int,
            current: CurrentUser = Depends(require_almacen_access()),
        ): ...
    """

    async def _checker(almacen_id: int, current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.tiene_acceso_almacen(almacen_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para operar sobre este almacén (RN-20)",
            )
        return current

    return _checker


DbSession = Depends(get_db)
