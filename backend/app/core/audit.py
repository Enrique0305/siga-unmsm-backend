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
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.event import listens_for

from app.models.auditoria import AuditoriaLog

current_usuario_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_usuario_id", default=None
)

_ACCIONES = {"new": "CREAR", "dirty": "ACTUALIZAR", "deleted": "ELIMINAR"}

# Nunca debe terminar en auditoria_log, ni siquiera como hash (única
# columna sensible en todo el esquema, confirmado con
# grep -rn "password\|secret\|token" app/models/*.py).
CAMPOS_EXCLUIDOS = {"password_hash"}


def _pk_de(obj) -> int | None:
    """None para PK compuesta (stock_almacen_producto, usuario_almacen_acceso,
    ...) — son tablas de estado/asociación, no "documentos" de RN-08."""
    mapper = inspect(obj).mapper
    pk_cols = mapper.primary_key
    if len(pk_cols) != 1:
        return None
    return getattr(obj, pk_cols[0].name)


def _valor_serializable(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _snapshot(obj, state) -> dict:
    """Para CREAR/ELIMINAR: todas las columnas ya cargadas en memoria.
    `attr.key in state.unloaded` es el guard real, no defensividad de
    más: columnas GENERATED ALWAYS ... STORED (ej. ProductoContratado.
    tope_monetario) quedan "expiradas" tras el INSERT en MySQL/aiomysql
    (producción) — leerlas sin refrescar dispara I/O implícito y revienta
    en async (CLAUDE.md sección 7.3). En SQLite (motor de los tests)
    INSERT ... RETURNING ya las resuelve, así que ahí `unloaded` nunca
    las excluye — el guard es transparente en ambos motores."""
    mapper = inspect(obj).mapper
    return {
        attr.key: _valor_serializable(getattr(obj, attr.key))
        for attr in mapper.column_attrs
        if attr.key not in state.unloaded and attr.key not in CAMPOS_EXCLUIDOS
    }


def _diff(obj, state) -> dict:
    """Para ACTUALIZAR: solo columnas que realmente cambiaron, vía
    `history` de cada atributo — mismo guard `unloaded` que _snapshot."""
    mapper = inspect(obj).mapper
    cambios = {}
    for attr in mapper.column_attrs:
        if attr.key in state.unloaded or attr.key in CAMPOS_EXCLUIDOS:
            continue
        hist = state.attrs[attr.key].history
        if not hist.has_changes():
            continue
        antes = hist.deleted[0] if hist.deleted else None
        despues = hist.added[0] if hist.added else getattr(obj, attr.key)
        cambios[attr.key] = {
            "antes": _valor_serializable(antes),
            "despues": _valor_serializable(despues),
        }
    return cambios


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
            state = inspect(obj)
            detalle = _diff(obj, state) if grupo == "dirty" else _snapshot(obj, state)
            session.add(
                AuditoriaLog(
                    entidad=obj.__tablename__,
                    entidad_id=pk,
                    accion=accion,
                    usuario_id=usuario_id,
                    detalle_json=detalle or None,
                )
            )
