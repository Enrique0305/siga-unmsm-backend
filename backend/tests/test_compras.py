"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo real del Módulo 3: orden de compra multialmacén (RN-01
saldo suficiente, RN-09 precio del contrato, RN-15 distribución = cantidad
solicitada, RN-19 saldo GLOBAL descontado en producto_contratado) -> pedido
semanal (RN-16 único por menú+almacén+semana) -> guía de remisión (RN-02
vinculada a OC+pedido semanal, RN-03 no exceder saldo pendiente de la
línea) -> anulación de OC (revierte saldo, bloqueada si ya hubo entregas).
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

    from app.models.catalogos import UnidadMedida
    from app.models.organizacion import Almacen, CentroConsumo, Sede

    async with TestSession() as seed_session:
        seed_session.add(UnidadMedida(unidad_id=1, codigo="KG", nombre="Kilogramo"))
        seed_session.add(Sede(sede_id=1, nombre="Sede Test"))
        await seed_session.flush()
        seed_session.add(
            Almacen(
                almacen_id=1,
                codigo="ALM-TEST-1",
                nombre="Almacén Test 1",
                sede_id=1,
                tipo_comedor="ESTUDIANTES",
                responsable_id=1,
            )
        )
        seed_session.add(
            Almacen(
                almacen_id=2,
                codigo="ALM-TEST-2",
                nombre="Almacén Test 2",
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


async def _preparar_contrato_con_producto(client: AsyncClient, headers: dict) -> dict:
    """Replica el flujo de Módulo 2 hasta tener un producto_contratado con
    saldo (cantidad_contratada=100, precio_unitario=5.5 -> saldo_fisico=100,
    saldo_monetario=550)."""
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

    proveedor_resp = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20123456789", "razon_social": "Proveedor Test SAC"}
    )
    proveedor_id = proveedor_resp.json()["proveedor_id"]

    fecha_inicio = date.today()
    fecha_fin = date.today() + timedelta(days=200)
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
        },
    )
    contrato_id = contrato_resp.json()["contrato_id"]

    pc_resp = await client.post(
        f"/api/v1/contratos/{contrato_id}/productos",
        headers=headers,
        json={"producto_id": producto_id, "precio_unitario": 5.5, "cantidad_contratada": 100},
    )
    producto_contratado_id = pc_resp.json()["producto_contratado_id"]

    menu_resp = await client.post(
        "/api/v1/planificacion/menus-quincenales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id,
            "quincena_inicio": fecha_inicio.isoformat(),
            "quincena_fin": (fecha_inicio + timedelta(days=14)).isoformat(),
        },
    )
    menu_id = menu_resp.json()["menu_id"]

    return {
        "producto_id": producto_id,
        "proveedor_id": proveedor_id,
        "contrato_id": contrato_id,
        "producto_contratado_id": producto_contratado_id,
        "menu_id": menu_id,
    }


@pytest.mark.asyncio
async def test_flujo_compras_completo(client: AsyncClient):
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    # 1) RN-01: cantidad solicitada excede el saldo físico (100) -> bloqueada
    oc_bloqueada = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-2026-001",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 200,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 200}],
                }
            ],
        },
    )
    assert oc_bloqueada.status_code == 422
    assert "RN-01" in oc_bloqueada.json()["detail"]

    # 2) RN-15: la distribución no suma la cantidad solicitada -> bloqueada
    oc_rn15 = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-2026-002",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 5}],
                }
            ],
        },
    )
    assert oc_rn15.status_code == 422
    assert "RN-15" in oc_rn15.json()["detail"]

    # 3) OC válida, distribuida entre 2 almacenes (60 = 40 + 20)
    oc_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-2026-003",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 60,
                    "distribucion": [
                        {"almacen_id": 1, "cantidad_distribuida": 40},
                        {"almacen_id": 2, "cantidad_distribuida": 20},
                    ],
                }
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    oc = oc_resp.json()
    assert oc["estado"] == "EMITIDA"
    linea = oc["detalle"][0]
    assert linea["precio_unitario_aplicado"] == pytest.approx(5.5)  # RN-09
    assert linea["saldo_oc"] == pytest.approx(60.0)
    assert len(linea["distribucion"]) == 2
    orden_compra_id = oc["orden_compra_id"]
    orden_compra_detalle_id = linea["orden_compra_detalle_id"]

    # 4) RN-01/RN-19: el saldo del producto contratado bajó globalmente (550 -> 220)
    contrato_resp = await client.get(f"/api/v1/contratos/{ctx['contrato_id']}", headers=headers)
    pc = contrato_resp.json()["productos_contratados"][0]
    assert pc["saldo_fisico"] == pytest.approx(40.0)
    assert pc["saldo_monetario"] == pytest.approx(220.0)

    # 5) pedido semanal
    semana_inicio = date.today()
    pedido_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": orden_compra_id,
            "menu_id": ctx["menu_id"],
            "almacen_id": 1,
            "semana_inicio": semana_inicio.isoformat(),
            "semana_fin": (semana_inicio + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido_resp.status_code == 201, pedido_resp.text
    pedido_semanal_id = pedido_resp.json()["pedido_semanal_id"]

    # 6) RN-16: mismo menú+almacén+semana_inicio -> 409
    pedido_dup = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": orden_compra_id,
            "menu_id": ctx["menu_id"],
            "almacen_id": 1,
            "semana_inicio": semana_inicio.isoformat(),
            "semana_fin": (semana_inicio + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido_dup.status_code == 409

    # 7) RN-03: la guía intenta entregar más de lo pendiente en la línea de OC (60)
    guia_bloqueada = await client.post(
        "/api/v1/guias-remision",
        headers=headers,
        json={
            "numero_guia": "GR-0001",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": pedido_semanal_id,
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 100}],
        },
    )
    assert guia_bloqueada.status_code == 422
    assert "RN-03" in guia_bloqueada.json()["detail"]

    # 8) guía válida: entrega completa de la línea (60)
    guia_resp = await client.post(
        "/api/v1/guias-remision",
        headers=headers,
        json={
            "numero_guia": "GR-0001",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": pedido_semanal_id,
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 60, "lote": "L-1"}],
        },
    )
    assert guia_resp.status_code == 201, guia_resp.text
    guia = guia_resp.json()
    assert guia["estado"] == "PENDIENTE"
    assert guia["proveedor_razon_social"] == "Proveedor Test SAC"
    assert guia["detalle"][0]["cantidad_entregada"] == pytest.approx(60.0)

    # 9) la línea de OC queda en saldo_oc = 0
    oc_actualizada = await client.get(f"/api/v1/ordenes-compra/{orden_compra_id}", headers=headers)
    linea_actualizada = oc_actualizada.json()["detalle"][0]
    assert linea_actualizada["cantidad_ingresada_acumulada"] == pytest.approx(60.0)
    assert linea_actualizada["saldo_oc"] == pytest.approx(0.0)
    assert linea_actualizada["total_excedente_autorizado"] == pytest.approx(0.0)

    # 9a) RN-03 "salvo autorización": sin autorización, un excedente de 5 sigue bloqueado
    excedente_bloqueado = await client.post(
        f"/api/v1/guias-remision/{guia['guia_remision_id']}/detalle",
        headers=headers,
        json={"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 5},
    )
    assert excedente_bloqueado.status_code == 422
    assert "RN-03" in excedente_bloqueado.json()["detail"]

    # 9b) se autoriza el excedente de 5 sobre esa línea de OC
    autorizacion_resp = await client.post(
        f"/api/v1/ordenes-compra/detalle/{orden_compra_detalle_id}/autorizaciones-excedente",
        headers=headers,
        json={"cantidad_excedente": 5, "justificacion": "Ajuste de peso del proveedor, autorizado por Logística"},
    )
    assert autorizacion_resp.status_code == 201, autorizacion_resp.text
    assert autorizacion_resp.json()["cantidad_excedente"] == pytest.approx(5.0)

    # 9c) con el excedente autorizado, la misma entrega de 5 ahora sí se registra
    excedente_ok = await client.post(
        f"/api/v1/guias-remision/{guia['guia_remision_id']}/detalle",
        headers=headers,
        json={"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 5},
    )
    assert excedente_ok.status_code == 201, excedente_ok.text

    oc_con_excedente = await client.get(f"/api/v1/ordenes-compra/{orden_compra_id}", headers=headers)
    linea_con_excedente = oc_con_excedente.json()["detalle"][0]
    assert linea_con_excedente["cantidad_ingresada_acumulada"] == pytest.approx(65.0)
    assert linea_con_excedente["total_excedente_autorizado"] == pytest.approx(5.0)
    assert len(linea_con_excedente["autorizaciones_excedente"]) == 1

    # 10) no se puede anular una OC con entregas ya registradas
    anular_bloqueado = await client.patch(
        f"/api/v1/ordenes-compra/{orden_compra_id}/estado", headers=headers, json={"estado": "ANULADA"}
    )
    assert anular_bloqueado.status_code == 422

    # 11) una segunda OC sin entregas sí se puede anular, y revierte el saldo
    oc2_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-2026-004",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 10}],
                }
            ],
        },
    )
    assert oc2_resp.status_code == 201, oc2_resp.text
    orden_compra_2_id = oc2_resp.json()["orden_compra_id"]

    contrato_tras_oc2 = await client.get(f"/api/v1/contratos/{ctx['contrato_id']}", headers=headers)
    assert contrato_tras_oc2.json()["productos_contratados"][0]["saldo_fisico"] == pytest.approx(30.0)

    anular_ok = await client.patch(
        f"/api/v1/ordenes-compra/{orden_compra_2_id}/estado", headers=headers, json={"estado": "ANULADA"}
    )
    assert anular_ok.status_code == 200, anular_ok.text
    assert anular_ok.json()["estado"] == "ANULADA"

    contrato_tras_anular = await client.get(f"/api/v1/contratos/{ctx['contrato_id']}", headers=headers)
    assert contrato_tras_anular.json()["productos_contratados"][0]["saldo_fisico"] == pytest.approx(40.0)
