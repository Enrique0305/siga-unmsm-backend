"""
Auditoría automática (RN-08: todo documento conserva historial_auditoria[]).

El actor (usuario_id) vive en el JWT/CurrentUser (api/deps.py), no en la
sesión de SQLAlchemy, y un evento de sesión no tiene acceso a la request de
FastAPI. El puente es un ContextVar que el middleware llena por request
(ver api/middleware.py) y que el evento de abajo lee.

Se registra una sola vez, a nivel de la clase base `Session` — cubre
automáticamente cualquier AsyncSession de la app (presente y futura) sin
tocar los ~30 archivos crud/*.py ya existentes.
"""
import contextvars

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.event import listens_for

from app.models.auditoria import AuditoriaLog

current_usuario_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_usuario_id", default=None
)

_ACCIONES = {"new": "CREAR", "dirty": "ACTUALIZAR", "deleted": "ELIMINAR"}


def _pk_de(obj) -> int | None:
    """None para PK compuesta (stock_almacen_producto, usuario_almacen_acceso,
    ...) — son tablas de estado/asociación, no "documentos" de RN-08."""
    mapper = inspect(obj).mapper
    pk_cols = mapper.primary_key
    if len(pk_cols) != 1:
        return None
    return getattr(obj, pk_cols[0].name)


@listens_for(Session, "after_flush")
def _registrar_auditoria(session: Session, flush_context) -> None:
    usuario_id = current_usuario_id.get()
    if usuario_id is None:
        # Scripts sin request HTTP (app/seed.py, siembras directas de tests)
        # no tienen un actor real que auditar.
        return

    grupos = {"new": session.new, "dirty": session.dirty, "deleted": session.deleted}
    for grupo, objetos in grupos.items():
        accion = _ACCIONES[grupo]
        for obj in objetos:
            if isinstance(obj, AuditoriaLog):
                continue  # evita recursión infinita
            if grupo == "dirty" and not session.is_modified(obj, include_collections=False):
                continue
            pk = _pk_de(obj)
            if pk is None:
                continue
            session.add(
                AuditoriaLog(
                    entidad=obj.__tablename__,
                    entidad_id=pk,
                    accion=accion,
                    usuario_id=usuario_id,
                )
            )
