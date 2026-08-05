"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Sesión 10: cierra los huecos que bloqueaban la pantalla de Administración
— GET /catalogos/roles y PATCH /usuarios/{id} (antes solo existían GET
lista/me y POST crear). Cubre: crear usuario -> login funciona -> catálogo
de roles -> PATCH cambia rol/estado/almacenes -> usuario inactivo no
puede loguear -> PATCH bloqueado para roles no-ADMIN.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401  registra los modelos
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(bind=engine, expire_on_commit=False)

    from app.models.contratos import Proveedor
    from app.models.organizacion import Almacen, Rol, Sede

    async with TestSession() as seed_session:
        seed_session.add(Rol(rol_id=1, nombre="ADMIN", acceso_todos_almacenes=True))
        seed_session.add(Rol(rol_id=2, nombre="NUTRICION", acceso_todos_almacenes=False))
        seed_session.add(Rol(rol_id=3, nombre="PROVEEDOR", acceso_todos_almacenes=False))
        seed_session.add(Sede(sede_id=1, nombre="Sede Test"))
        seed_session.add(Proveedor(proveedor_id=1, ruc="20123456789", razon_social="Proveedor Test SAC"))
        await seed_session.flush()
        seed_session.add(
            Almacen(
                almacen_id=1,
                codigo="ALM-TEST",
                nombre="Almacén Test",
                sede_id=1,
                tipo_comedor="ESTUDIANTES",
                responsable_id=1,
            )
        )
        await seed_session.commit()

    async def _get_db_override():
        async with TestSession() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _get_db_override

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


def _headers_admin():
    token = create_access_token(usuario_id=1, rol="ADMIN", almacenes=[], acceso_todos_almacenes=True)
    return {"Authorization": f"Bearer {token}"}


def _headers_nutricion():
    token = create_access_token(usuario_id=99, rol="NUTRICION", almacenes=[1], acceso_todos_almacenes=False)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_catalogo_roles(client: AsyncClient):
    resp = await client.get("/api/v1/catalogos/roles", headers=_headers_admin())
    assert resp.status_code == 200, resp.text
    nombres = {r["nombre"] for r in resp.json()}
    assert nombres == {"ADMIN", "NUTRICION", "PROVEEDOR"}


@pytest.mark.asyncio
async def test_crear_usuario_login_y_patch(client: AsyncClient):
    admin_headers = _headers_admin()

    crear = await client.post(
        "/api/v1/usuarios",
        headers=admin_headers,
        json={
            "nombres": "Ana",
            "apellidos": "Torres",
            "correo": "ana.torres@unmsm.edu.pe",
            "password": "ClaveSegura123",
            "rol_id": 2,
            "sede_id": 1,
            "almacen_ids": [1],
        },
    )
    assert crear.status_code == 201, crear.text
    usuario = crear.json()
    assert usuario["estado"] == "ACTIVO"
    assert usuario["rol"]["nombre"] == "NUTRICION"
    assert usuario["almacen_ids"] == [1]
    usuario_id = usuario["usuario_id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"correo": "ana.torres@unmsm.edu.pe", "password": "ClaveSegura123"},
    )
    assert login.status_code == 200, login.text

    patch = await client.patch(
        f"/api/v1/usuarios/{usuario_id}",
        headers=admin_headers,
        json={"rol_id": 1, "estado": "INACTIVO", "almacen_ids": []},
    )
    assert patch.status_code == 200, patch.text
    actualizado = patch.json()
    assert actualizado["estado"] == "INACTIVO"
    assert actualizado["rol"]["nombre"] == "ADMIN"
    assert actualizado["almacen_ids"] == []

    login_inactivo = await client.post(
        "/api/v1/auth/login",
        json={"correo": "ana.torres@unmsm.edu.pe", "password": "ClaveSegura123"},
    )
    assert login_inactivo.status_code == 403


@pytest.mark.asyncio
async def test_patch_usuario_requiere_admin(client: AsyncClient):
    resp = await client.patch(
        "/api/v1/usuarios/1",
        headers=_headers_nutricion(),
        json={"estado": "INACTIVO"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_crear_usuario_proveedor_con_proveedor_id(client: AsyncClient):
    """Sesión 12: Usuario.proveedor_id acota qué documentos puede ver un
    usuario con rol PROVEEDOR — confirma que el campo se guarda y se
    refleja en UsuarioOut, y que se puede actualizar vía PATCH."""
    admin_headers = _headers_admin()

    crear = await client.post(
        "/api/v1/usuarios",
        headers=admin_headers,
        json={
            "nombres": "Beto",
            "apellidos": "Proveedor",
            "correo": "beto.proveedor@unmsm.edu.pe",
            "password": "ClaveSegura123",
            "rol_id": 3,
            "proveedor_id": 1,
        },
    )
    assert crear.status_code == 201, crear.text
    usuario = crear.json()
    assert usuario["rol"]["nombre"] == "PROVEEDOR"
    assert usuario["proveedor_id"] == 1
    usuario_id = usuario["usuario_id"]

    patch = await client.patch(
        f"/api/v1/usuarios/{usuario_id}",
        headers=admin_headers,
        json={"proveedor_id": None},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["proveedor_id"] is None
