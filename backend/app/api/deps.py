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
    proveedor_id: int | None = None

    def tiene_acceso_almacen(self, almacen_id: int) -> bool:
        return self.acceso_todos_almacenes or almacen_id in self.almacenes

    def tiene_acceso_proveedor(self, proveedor_id: int) -> bool:
        """A diferencia de tiene_acceso_almacen, esto no restringe a nadie
        salvo al propio rol PROVEEDOR — ADMIN/LOGISTICA_CENTRAL siempre
        pasan (Sesión 12, alcance de PROVEEDOR)."""
        return self.rol != "PROVEEDOR" or self.proveedor_id == proveedor_id


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
        proveedor_id=payload.get("proveedor_id"),
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


def verificar_acceso_almacen(current: CurrentUser, almacen_id: int) -> None:
    """RN-20 para endpoints donde almacen_id viene del body o se deriva de
    otra entidad (guía, transferencia, etc.), no de un path param — por eso
    no puede resolverse con `require_almacen_access()`. Mismo mensaje/
    status que esa dependency factory, para consistencia."""
    if not current.tiene_acceso_almacen(almacen_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para operar sobre este almacén (RN-20)",
        )


def resolver_almacenes_visibles(current: CurrentUser, almacen_id: int | None) -> list[int] | None:
    """RN-20 en lecturas (Sesión 15): calcula el filtro `IN` a aplicar en un
    listado para un rol sin `acceso_todos_almacenes`. `None` => sin
    restricción (llamar solo cuando `current.acceso_todos_almacenes` es
    False; para roles con acceso total no hace falta ni debe usarse).
    Si el cliente pidió un `almacen_id` fuera de su alcance, retorna una
    lista vacía (SQLAlchemy compila `.in_([])` como una condición siempre
    falsa, cero filas) en vez de un 403 — evita filtrar si ese almacén
    existe o no."""
    if almacen_id is not None:
        return [almacen_id] if current.tiene_acceso_almacen(almacen_id) else []
    return current.almacenes


def verificar_acceso_proveedor(current: CurrentUser, proveedor_id: int) -> None:
    """Sesión 12: un usuario con rol PROVEEDOR solo puede leer/escribir
    documentos (contrato, OC, guía) de su propio proveedor_id — cualquier
    otro rol pasa siempre."""
    if not current.tiene_acceso_proveedor(proveedor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para operar sobre los documentos de este proveedor",
        )


DbSession = Depends(get_db)
