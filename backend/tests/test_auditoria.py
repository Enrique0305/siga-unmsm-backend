"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica que el evento global de auditoría (app/core/audit.py) registra
automáticamente cada creación/actualización, sin que ningún crud/*.py haya
tenido que llamarlo explícitamente.
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from tests.test_compras import _headers_admin, client  # noqa: F401


def _headers_rol(rol: str) -> dict:
    token = create_access_token(usuario_id=3, rol=rol, almacenes=[], acceso_todos_almacenes=(rol == "LOGISTICA_CENTRAL"))
    return {"Authorization": f"Bearer {token}"}


def _headers_rol_con_usuario_id(rol: str, usuario_id: int) -> dict:
    token = create_access_token(usuario_id=usuario_id, rol=rol, almacenes=[], acceso_todos_almacenes=True)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_auditoria_automatica_crear_y_actualizar(client: AsyncClient):
    headers = _headers_admin()

    crear_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P001", "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert crear_resp.status_code == 201, crear_resp.text
    producto_id = crear_resp.json()["producto_id"]

    auditoria_tras_crear = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id}
    )
    assert auditoria_tras_crear.status_code == 200
    items_crear = auditoria_tras_crear.json()["items"]
    assert len(items_crear) == 1
    assert items_crear[0]["accion"] == "CREAR"
    assert items_crear[0]["entidad"] == "producto"
    assert items_crear[0]["entidad_id"] == producto_id
    assert items_crear[0]["usuario_id"] == 1  # _headers_admin usa usuario_id=1
    # sin una fila Usuario real sembrada (ver más abajo), usuario_nombre
    # cae al fallback en vez de romper con un AttributeError
    assert items_crear[0]["usuario_nombre"] == "Usuario #1"
    # deuda técnica: detalle_json ya no es None, trae el snapshot completo
    assert items_crear[0]["detalle_json"]["codigo"] == "P001"
    assert items_crear[0]["detalle_json"]["nombre"] == "Arroz superior"

    actualizar_resp = await client.patch(
        f"/api/v1/productos/{producto_id}", headers=headers, json={"nombre": "Arroz superior premium"}
    )
    assert actualizar_resp.status_code == 200, actualizar_resp.text

    auditoria_tras_actualizar = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id}
    )
    items_actualizar = auditoria_tras_actualizar.json()["items"]
    assert len(items_actualizar) == 2
    acciones = {item["accion"] for item in items_actualizar}
    assert acciones == {"CREAR", "ACTUALIZAR"}

    item_actualizar = next(i for i in items_actualizar if i["accion"] == "ACTUALIZAR")
    # solo la columna que cambió aparece en el diff — "codigo" no se tocó
    assert item_actualizar["detalle_json"] == {
        "nombre": {"antes": "Arroz superior", "despues": "Arroz superior premium"}
    }

    # otra entidad no aparece en el filtro
    auditoria_otra_entidad = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id + 999}
    )
    assert auditoria_otra_entidad.json()["items"] == []


@pytest.mark.asyncio
async def test_auditoria_usuario_nombre_real(client: AsyncClient):
    """Deuda técnica: con una fila Usuario real sembrada, usuario_nombre
    trae nombres+apellidos en vez del fallback "Usuario #{id}"."""
    from app.core.security import hash_password
    from app.models.organizacion import Rol
    from app.models.usuario import Usuario

    async with client.session_factory() as db:
        rol = Rol(nombre="ADMIN_TEST", acceso_todos_almacenes=True)
        db.add(rol)
        await db.flush()
        usuario = Usuario(
            nombres="Ana",
            apellidos="Torres",
            correo="ana.torres@unmsm.edu.pe",
            password_hash=hash_password("Password123!"),
            rol_id=rol.rol_id,
        )
        db.add(usuario)
        await db.commit()
        usuario_id = usuario.usuario_id

    headers = _headers_rol_con_usuario_id("ADMIN", usuario_id)

    crear_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P-AUD-REAL", "nombre": "Aceite", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert crear_resp.status_code == 201, crear_resp.text
    producto_id = crear_resp.json()["producto_id"]

    auditoria_resp = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id}
    )
    assert auditoria_resp.status_code == 200, auditoria_resp.text
    item = auditoria_resp.json()["items"][0]
    assert item["usuario_id"] == usuario_id
    assert item["usuario_nombre"] == "Ana Torres"

    # deuda técnica: password_hash nunca debe aparecer en auditoria_log, ni
    # siquiera como hash. La fila Usuario se sembró con una sesión cruda
    # (sin ContextVar de actor, no genera auditoría — ver core/audit.py),
    # así que se dispara una actualización real vía API para tener una
    # fila ACTUALIZAR de "usuario" que sí pase por el evento.
    patch_resp = await client.patch(
        f"/api/v1/usuarios/{usuario_id}", headers=headers, json={"estado": "INACTIVO"}
    )
    assert patch_resp.status_code == 200, patch_resp.text

    auditoria_usuario = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "usuario", "entidad_id": usuario_id}
    )
    assert auditoria_usuario.status_code == 200, auditoria_usuario.text
    items_usuario = auditoria_usuario.json()["items"]
    assert len(items_usuario) == 1
    assert items_usuario[0]["accion"] == "ACTUALIZAR"
    assert "password_hash" not in items_usuario[0]["detalle_json"]
    assert items_usuario[0]["detalle_json"] == {
        "estado": {"antes": "ACTIVO", "despues": "INACTIVO"}
    }


@pytest.mark.asyncio
async def test_auditoria_requiere_rol_autorizado(client: AsyncClient):
    """Mismo gate que /reportes (frontend/lib/nav.ts: ADMIN, LOGISTICA_CENTRAL)."""
    bloqueado = await client.get("/api/v1/auditoria", headers=_headers_rol("ALMACENERO"))
    assert bloqueado.status_code == 403, bloqueado.text

    permitido = await client.get("/api/v1/auditoria", headers=_headers_rol("LOGISTICA_CENTRAL"))
    assert permitido.status_code == 200, permitido.text
