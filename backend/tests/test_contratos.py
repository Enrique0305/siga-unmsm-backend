"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo real del Módulo 2: producto -> ración anual -> requerimiento
anual (con detalle) -> aprobación -> proveedor -> contrato (bloqueado si el
requerimiento no está aprobado) -> producto contratado (saldo inicializado) ->
transiciones de estado de contrato.
"""
from datetime import date, timedelta

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

    # Semilla mínima: unidad de medida, sede, almacén y centro de consumo
    # (en producción los crea el catálogo base / módulo multialmacén; aquí
    # no hay endpoint de alta para sede/almacén todavía).
    from app.models.catalogos import UnidadMedida
    from app.models.organizacion import Almacen, CentroConsumo, Sede

    async with TestSession() as seed_session:
        seed_session.add(UnidadMedida(unidad_id=1, codigo="KG", nombre="Kilogramo"))
        seed_session.add(Sede(sede_id=1, nombre="Sede Test"))
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
        await seed_session.flush()
        seed_session.add(CentroConsumo(centro_consumo_id=1, sede_id=1, almacen_id=1, nombre="Comedor Test"))
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


def _headers_proveedor(proveedor_id: int) -> dict:
    token = create_access_token(
        usuario_id=2, rol="PROVEEDOR", almacenes=[], acceso_todos_almacenes=False, proveedor_id=proveedor_id
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_flujo_contrato_completo(client: AsyncClient):
    headers = _headers_admin()

    # 1) producto (catálogo logístico, prerrequisito de producto_contratado)
    producto_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P001", "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert producto_resp.status_code == 201, producto_resp.text
    producto_id = producto_resp.json()["producto_id"]

    # 2) ración anual (endpoint ya existente del Módulo 1)
    racion_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2026, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    assert racion_resp.status_code == 201, racion_resp.text
    racion_anual_id = racion_resp.json()["racion_anual_id"]

    # 3) requerimiento anual con una línea de detalle
    req_resp = await client.post(
        "/api/v1/requerimientos-anuales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id,
            "presupuesto_referencial_total": 5000,
            "detalle": [
                {
                    "producto_id": producto_id,
                    "cantidad_estimada_anual": 1000,
                    "unidad_id": 1,
                    "presupuesto_referencial": 5000,
                }
            ],
        },
    )
    assert req_resp.status_code == 201, req_resp.text
    requerimiento = req_resp.json()
    assert requerimiento["estado"] == "BORRADOR"
    assert requerimiento["detalle"][0]["producto_codigo"] == "P001"
    requerimiento_anual_id = requerimiento["requerimiento_anual_id"]

    # 4) proveedor
    proveedor_resp = await client.post(
        "/api/v1/proveedores",
        headers=headers,
        json={"ruc": "20123456789", "razon_social": "Proveedor Test SAC"},
    )
    assert proveedor_resp.status_code == 201, proveedor_resp.text
    proveedor_id = proveedor_resp.json()["proveedor_id"]

    fecha_inicio = date.today()
    fecha_fin = date.today() + timedelta(days=15)  # dentro de los 30 días -> alerta_vigencia

    # 5) el requerimiento anual todavía está en BORRADOR -> el contrato debe bloquearse
    contrato_bloqueado = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-2026-001",
            "proveedor_id": proveedor_id,
            "requerimiento_anual_id": requerimiento_anual_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "presupuesto_total": 5000,
        },
    )
    assert contrato_bloqueado.status_code == 422
    assert "APROBADO" in contrato_bloqueado.json()["detail"]

    # 6) aprobar el requerimiento: BORRADOR -> EN_REVISION -> APROBADO
    for estado in ("EN_REVISION", "APROBADO"):
        r = await client.patch(
            f"/api/v1/requerimientos-anuales/{requerimiento_anual_id}/estado",
            headers=headers,
            json={"estado": estado},
        )
        assert r.status_code == 200, r.text

    # 7) ahora sí se puede crear el contrato, con una entrega en el cronograma
    contrato_resp = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-2026-001",
            "proveedor_id": proveedor_id,
            "requerimiento_anual_id": requerimiento_anual_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "presupuesto_total": 5000,
            "cronograma": [{"periodo": "MENSUAL", "fecha_programada": fecha_inicio.isoformat()}],
        },
    )
    assert contrato_resp.status_code == 201, contrato_resp.text
    contrato = contrato_resp.json()
    assert contrato["estado"] == "VIGENTE"
    assert contrato["proveedor_razon_social"] == "Proveedor Test SAC"
    assert contrato["alerta_vigencia"] is True  # RN-12: <= 30 días para vencer
    assert len(contrato["cronograma"]) == 1
    contrato_id = contrato["contrato_id"]

    # 8) numero_contrato duplicado -> 409
    dup_resp = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-2026-001",
            "proveedor_id": proveedor_id,
            "requerimiento_anual_id": requerimiento_anual_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "presupuesto_total": 5000,
        },
    )
    assert dup_resp.status_code == 409

    # 9) producto contratado: saldo físico/monetario se inicializa (RN-19, global)
    pc_resp = await client.post(
        f"/api/v1/contratos/{contrato_id}/productos",
        headers=headers,
        json={"producto_id": producto_id, "precio_unitario": 5.5, "cantidad_contratada": 100},
    )
    assert pc_resp.status_code == 201, pc_resp.text
    producto_contratado = pc_resp.json()
    assert producto_contratado["tope_monetario"] == pytest.approx(550.0)
    assert producto_contratado["saldo_fisico"] == pytest.approx(100.0)
    assert producto_contratado["saldo_monetario"] == pytest.approx(550.0)
    assert producto_contratado["porcentaje_saldo_fisico"] == pytest.approx(100.0)
    assert producto_contratado["alerta_saldo"] is False

    # 10) mismo producto otra vez en el mismo contrato -> 409 (UNIQUE contrato+producto)
    pc_dup = await client.post(
        f"/api/v1/contratos/{contrato_id}/productos",
        headers=headers,
        json={"producto_id": producto_id, "precio_unitario": 5.5, "cantidad_contratada": 50},
    )
    assert pc_dup.status_code == 409

    # 11) transición de estado inválida
    bad_estado = await client.patch(
        f"/api/v1/contratos/{contrato_id}/estado", headers=headers, json={"estado": "CANCELADO"}
    )
    assert bad_estado.status_code == 422

    # 12) cierre válido: VIGENTE -> CERRADO
    cierre = await client.patch(
        f"/api/v1/contratos/{contrato_id}/estado", headers=headers, json={"estado": "CERRADO"}
    )
    assert cierre.status_code == 200, cierre.text
    assert cierre.json()["estado"] == "CERRADO"

    # 13) CERRADO es terminal
    reabrir = await client.patch(
        f"/api/v1/contratos/{contrato_id}/estado", headers=headers, json={"estado": "VIGENTE"}
    )
    assert reabrir.status_code == 422


@pytest.mark.asyncio
async def test_rn_alcance_proveedor(client: AsyncClient):
    """Sesión 12: un usuario con rol PROVEEDOR solo ve sus propios
    contratos, aunque no mande proveedor_id en la query, y no puede leer
    el detalle del contrato de otro proveedor."""
    headers = _headers_admin()

    producto_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P001", "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1},
    )
    producto_id = producto_resp.json()["producto_id"]

    racion_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2026, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    racion_anual_id = racion_resp.json()["racion_anual_id"]

    req_resp = await client.post(
        "/api/v1/requerimientos-anuales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id,
            "presupuesto_referencial_total": 5000,
            "detalle": [
                {"producto_id": producto_id, "cantidad_estimada_anual": 1000, "unidad_id": 1, "presupuesto_referencial": 5000}
            ],
        },
    )
    requerimiento_anual_id = req_resp.json()["requerimiento_anual_id"]
    for estado in ("EN_REVISION", "APROBADO"):
        await client.patch(
            f"/api/v1/requerimientos-anuales/{requerimiento_anual_id}/estado", headers=headers, json={"estado": estado}
        )

    fecha_inicio = date.today()
    fecha_fin = date.today() + timedelta(days=200)

    proveedor_a = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20111111111", "razon_social": "Proveedor A"}
    )
    proveedor_a_id = proveedor_a.json()["proveedor_id"]
    proveedor_b = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20222222222", "razon_social": "Proveedor B"}
    )
    proveedor_b_id = proveedor_b.json()["proveedor_id"]

    contrato_a = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-A-001",
            "proveedor_id": proveedor_a_id,
            "requerimiento_anual_id": requerimiento_anual_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "presupuesto_total": 5000,
        },
    )
    assert contrato_a.status_code == 201, contrato_a.text
    contrato_a_id = contrato_a.json()["contrato_id"]

    contrato_b = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-B-001",
            "proveedor_id": proveedor_b_id,
            "requerimiento_anual_id": requerimiento_anual_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "presupuesto_total": 5000,
        },
    )
    assert contrato_b.status_code == 201, contrato_b.text
    contrato_b_id = contrato_b.json()["contrato_id"]

    headers_proveedor_a = _headers_proveedor(proveedor_a_id)

    # lista: proveedor A solo ve su propio contrato, aunque no filtre por query
    lista = await client.get("/api/v1/contratos", headers=headers_proveedor_a)
    assert lista.status_code == 200, lista.text
    numeros = {c["numero_contrato"] for c in lista.json()["items"]}
    assert numeros == {"CTR-A-001"}

    # intentar forzar el filtro a otro proveedor por query no cambia nada
    lista_forzada = await client.get(
        f"/api/v1/contratos?proveedor_id={proveedor_b_id}", headers=headers_proveedor_a
    )
    assert lista_forzada.status_code == 200, lista_forzada.text
    assert {c["numero_contrato"] for c in lista_forzada.json()["items"]} == {"CTR-A-001"}

    # detalle: proveedor A puede ver su propio contrato...
    detalle_propio = await client.get(f"/api/v1/contratos/{contrato_a_id}", headers=headers_proveedor_a)
    assert detalle_propio.status_code == 200, detalle_propio.text

    # ...pero no el de otro proveedor
    detalle_ajeno = await client.get(f"/api/v1/contratos/{contrato_b_id}", headers=headers_proveedor_a)
    assert detalle_ajeno.status_code == 403
