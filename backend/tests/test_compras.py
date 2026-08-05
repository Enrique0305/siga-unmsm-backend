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


def _headers_rol(rol: str, almacenes: list[int], proveedor_id: int | None = None) -> dict:
    token = create_access_token(
        usuario_id=2, rol=rol, almacenes=almacenes, acceso_todos_almacenes=False, proveedor_id=proveedor_id
    )
    return {"Authorization": f"Bearer {token}"}


async def _preparar_contrato_con_producto(
    client: AsyncClient,
    headers: dict,
    producto_codigo: str = "P001",
    proveedor_ruc: str = "20123456789",
    proveedor_razon_social: str = "Proveedor Test SAC",
    numero_contrato: str = "CTR-2026-001",
) -> dict:
    """Replica el flujo de Módulo 2 hasta tener un producto_contratado con
    saldo (cantidad_contratada=100, precio_unitario=5.5 -> saldo_fisico=100,
    saldo_monetario=550). Los overrides opcionales permiten llamarla más de
    una vez en el mismo test (Sesión 12: dos proveedores independientes)."""
    producto_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": producto_codigo, "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1},
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
        "/api/v1/proveedores",
        headers=headers,
        json={"ruc": proveedor_ruc, "razon_social": proveedor_razon_social},
    )
    proveedor_id = proveedor_resp.json()["proveedor_id"]

    fecha_inicio = date.today()
    fecha_fin = date.today() + timedelta(days=200)
    contrato_resp = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": numero_contrato,
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


@pytest.mark.asyncio
async def test_rn20_alcance_por_almacen(client: AsyncClient):
    """RN-20: pedidos_semanales.py, ordenes_compra.py y guias_remision.py
    ahora validan que el usuario tenga acceso al almacén involucrado antes
    de escribir (antes solo Almacén/Cocina lo hacían)."""
    headers_admin = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers_admin)

    headers_sin_acceso = _headers_rol("LOGISTICA_CENTRAL", almacenes=[1])
    headers_con_acceso = _headers_rol("LOGISTICA_CENTRAL", almacenes=[2])

    # 1) pedido semanal: NUTRICION sin acceso al almacén 2 -> 403 (el check
    # corre antes de cualquier validación de FK, así que no hace falta una
    # OC/menú reales para probarlo).
    pedido_bloqueado = await client.post(
        "/api/v1/pedidos-semanales",
        headers=_headers_rol("NUTRICION", almacenes=[1]),
        json={
            "orden_compra_id": 1,
            "menu_id": ctx["menu_id"],
            "almacen_id": 2,
            "semana_inicio": date.today().isoformat(),
            "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido_bloqueado.status_code == 403
    assert "RN-20" in pedido_bloqueado.json()["detail"]

    # 2) OC: distribución completa en un almacén sin acceso -> 403
    oc_bloqueada = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers_sin_acceso,
        json={
            "numero_oc": "OC-RN20-001",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 2, "cantidad_distribuida": 10}],
                }
            ],
        },
    )
    assert oc_bloqueada.status_code == 403
    assert "RN-20" in oc_bloqueada.json()["detail"]

    # 2b) ALL, no ANY: distribución entre almacén 1 (autorizado) y 2 (no) -> 403 igual
    oc_bloqueada_parcial = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers_sin_acceso,
        json={
            "numero_oc": "OC-RN20-002",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [
                        {"almacen_id": 1, "cantidad_distribuida": 5},
                        {"almacen_id": 2, "cantidad_distribuida": 5},
                    ],
                }
            ],
        },
    )
    assert oc_bloqueada_parcial.status_code == 403

    # 3) OC creada por admin, distribuida solo en el almacén 2, para probar
    # el bloqueo de PATCH estado y autorizar-excedente sobre un usuario
    # restringido al almacén 1.
    oc_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers_admin,
        json={
            "numero_oc": "OC-RN20-003",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 2, "cantidad_distribuida": 10}],
                }
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    oc = oc_resp.json()
    orden_compra_id = oc["orden_compra_id"]
    orden_compra_detalle_id = oc["detalle"][0]["orden_compra_detalle_id"]

    estado_bloqueado = await client.patch(
        f"/api/v1/ordenes-compra/{orden_compra_id}/estado", headers=headers_sin_acceso, json={"estado": "ANULADA"}
    )
    assert estado_bloqueado.status_code == 403

    excedente_bloqueado = await client.post(
        f"/api/v1/ordenes-compra/detalle/{orden_compra_detalle_id}/autorizaciones-excedente",
        headers=headers_sin_acceso,
        json={"cantidad_excedente": 1, "justificacion": "test"},
    )
    assert excedente_bloqueado.status_code == 403

    # y con acceso al almacén 2, sí puede
    estado_ok = await client.patch(
        f"/api/v1/ordenes-compra/{orden_compra_id}/estado", headers=headers_con_acceso, json={"estado": "ANULADA"}
    )
    assert estado_ok.status_code == 200, estado_ok.text

    # 4) guía de remisión: PROVEEDOR sin acceso al almacén destino -> 403
    # proveedor_id igual en ambos tokens: aísla el chequeo a la dimensión
    # de almacén (RN-20), el de proveedor (Sesión 12) se prueba aparte.
    headers_proveedor_sin_acceso = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=ctx["proveedor_id"])
    headers_proveedor_con_acceso = _headers_rol("PROVEEDOR", almacenes=[2], proveedor_id=ctx["proveedor_id"])

    guia_bloqueada = await client.post(
        "/api/v1/guias-remision",
        headers=headers_proveedor_sin_acceso,
        json={
            "numero_guia": "GR-RN20-001",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": 1,
            "almacen_destino_id": 2,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 1}],
        },
    )
    assert guia_bloqueada.status_code == 403
    assert "RN-20" in guia_bloqueada.json()["detail"]

    # 5) agregar línea a una guía existente: se prepara una guía real sobre
    # el almacén 2 (admin) y se intenta agregar una línea como PROVEEDOR sin
    # acceso a ese almacén.
    oc2_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers_admin,
        json={
            "numero_oc": "OC-RN20-004",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 2, "cantidad_distribuida": 10}],
                }
            ],
        },
    )
    assert oc2_resp.status_code == 201, oc2_resp.text
    oc2 = oc2_resp.json()
    orden_compra_2_id = oc2["orden_compra_id"]
    orden_compra_detalle_2_id = oc2["detalle"][0]["orden_compra_detalle_id"]

    pedido2_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers_admin,
        json={
            "orden_compra_id": orden_compra_2_id,
            "menu_id": ctx["menu_id"],
            "almacen_id": 2,
            "semana_inicio": date.today().isoformat(),
            "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido2_resp.status_code == 201, pedido2_resp.text

    guia2_resp = await client.post(
        "/api/v1/guias-remision",
        headers=headers_admin,
        json={
            "numero_guia": "GR-RN20-002",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_2_id,
            "pedido_semanal_id": pedido2_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 2,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": orden_compra_detalle_2_id, "cantidad_entregada": 5}],
        },
    )
    assert guia2_resp.status_code == 201, guia2_resp.text
    guia2_id = guia2_resp.json()["guia_remision_id"]

    detalle_bloqueado = await client.post(
        f"/api/v1/guias-remision/{guia2_id}/detalle",
        headers=headers_proveedor_sin_acceso,
        json={"orden_compra_detalle_id": orden_compra_detalle_2_id, "cantidad_entregada": 1},
    )
    assert detalle_bloqueado.status_code == 403

    detalle_ok = await client.post(
        f"/api/v1/guias-remision/{guia2_id}/detalle",
        headers=headers_proveedor_con_acceso,
        json={"orden_compra_detalle_id": orden_compra_detalle_2_id, "cantidad_entregada": 1},
    )
    assert detalle_ok.status_code == 201, detalle_ok.text


@pytest.mark.asyncio
async def test_rn_alcance_proveedor(client: AsyncClient):
    """Sesión 12: un usuario con rol PROVEEDOR solo ve/toca las OCs y
    guías de su propio proveedor_id, y no puede impersonar a otro
    proveedor al crear una guía."""
    headers = _headers_admin()
    ctx_a = await _preparar_contrato_con_producto(
        client,
        headers,
        producto_codigo="P-PROV-A",
        proveedor_ruc="20111111111",
        proveedor_razon_social="Proveedor A",
        numero_contrato="CTR-PROV-A",
    )
    ctx_b = await _preparar_contrato_con_producto(
        client,
        headers,
        producto_codigo="P-PROV-B",
        proveedor_ruc="20222222222",
        proveedor_razon_social="Proveedor B",
        numero_contrato="CTR-PROV-B",
    )

    async def _crear_oc_pedido_guia(ctx: dict, numero_oc: str, numero_guia: str) -> dict:
        oc_resp = await client.post(
            "/api/v1/ordenes-compra",
            headers=headers,
            json={
                "numero_oc": numero_oc,
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
        assert oc_resp.status_code == 201, oc_resp.text
        oc = oc_resp.json()
        orden_compra_detalle_id = oc["detalle"][0]["orden_compra_detalle_id"]

        pedido_resp = await client.post(
            "/api/v1/pedidos-semanales",
            headers=headers,
            json={
                "orden_compra_id": oc["orden_compra_id"],
                "menu_id": ctx["menu_id"],
                "almacen_id": 1,
                "semana_inicio": date.today().isoformat(),
                "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
            },
        )
        assert pedido_resp.status_code == 201, pedido_resp.text

        guia_resp = await client.post(
            "/api/v1/guias-remision",
            headers=headers,
            json={
                "numero_guia": numero_guia,
                "proveedor_id": ctx["proveedor_id"],
                "orden_compra_id": oc["orden_compra_id"],
                "pedido_semanal_id": pedido_resp.json()["pedido_semanal_id"],
                "almacen_destino_id": 1,
                "fecha_entrega": date.today().isoformat(),
                "detalle": [{"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": 5}],
            },
        )
        assert guia_resp.status_code == 201, guia_resp.text

        return {
            "orden_compra_id": oc["orden_compra_id"],
            "orden_compra_detalle_id": orden_compra_detalle_id,
            "guia_remision_id": guia_resp.json()["guia_remision_id"],
        }

    docs_a = await _crear_oc_pedido_guia(ctx_a, "OC-PROV-A-001", "GR-PROV-A-001")
    docs_b = await _crear_oc_pedido_guia(ctx_b, "OC-PROV-B-001", "GR-PROV-B-001")

    headers_proveedor_a = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=ctx_a["proveedor_id"])

    # OC: lista filtrada, detalle ajeno bloqueado
    lista_oc = await client.get("/api/v1/ordenes-compra", headers=headers_proveedor_a)
    assert lista_oc.status_code == 200, lista_oc.text
    assert {o["numero_oc"] for o in lista_oc.json()["items"]} == {"OC-PROV-A-001"}

    detalle_oc_ajena = await client.get(f"/api/v1/ordenes-compra/{docs_b['orden_compra_id']}", headers=headers_proveedor_a)
    assert detalle_oc_ajena.status_code == 403

    detalle_oc_propia = await client.get(f"/api/v1/ordenes-compra/{docs_a['orden_compra_id']}", headers=headers_proveedor_a)
    assert detalle_oc_propia.status_code == 200, detalle_oc_propia.text

    # Guía: lista filtrada, detalle ajeno bloqueado
    lista_guia = await client.get("/api/v1/guias-remision", headers=headers_proveedor_a)
    assert lista_guia.status_code == 200, lista_guia.text
    assert {g["numero_guia"] for g in lista_guia.json()["items"]} == {"GR-PROV-A-001"}

    detalle_guia_ajena = await client.get(f"/api/v1/guias-remision/{docs_b['guia_remision_id']}", headers=headers_proveedor_a)
    assert detalle_guia_ajena.status_code == 403

    # Impersonación: proveedor A intenta crear una guía con el proveedor_id de B -> 403
    guia_impersonada = await client.post(
        "/api/v1/guias-remision",
        headers=headers_proveedor_a,
        json={
            "numero_guia": "GR-IMPERSONACION",
            "proveedor_id": ctx_b["proveedor_id"],
            "orden_compra_id": docs_b["orden_compra_id"],
            "pedido_semanal_id": 1,
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": docs_b["orden_compra_detalle_id"], "cantidad_entregada": 1}],
        },
    )
    assert guia_impersonada.status_code == 403

    # Agregar línea a una guía ajena -> 403
    detalle_bloqueado = await client.post(
        f"/api/v1/guias-remision/{docs_b['guia_remision_id']}/detalle",
        headers=headers_proveedor_a,
        json={"orden_compra_detalle_id": docs_b["orden_compra_detalle_id"], "cantidad_entregada": 1},
    )
    assert detalle_bloqueado.status_code == 403


@pytest.mark.asyncio
async def test_rn20_lecturas_ordenes_compra_pedidos_guias(client: AsyncClient):
    """Sesión 15: cierra RN-20 en las lecturas (GET) — hasta la Sesión 11
    solo las escrituras estaban acotadas por almacén. Un usuario restringido
    al almacén 1 no debe ver, ni en la lista ni en el detalle, documentos de
    otro almacén."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    async def _crear_oc(numero_oc: str, distribucion: list[dict]) -> dict:
        oc_resp = await client.post(
            "/api/v1/ordenes-compra",
            headers=headers,
            json={
                "numero_oc": numero_oc,
                "contrato_id": ctx["contrato_id"],
                "periodo_mes": date.today().replace(day=1).isoformat(),
                "detalle": [
                    {
                        "producto_contratado_id": ctx["producto_contratado_id"],
                        "cantidad_solicitada": sum(d["cantidad_distribuida"] for d in distribucion),
                        "distribucion": distribucion,
                    }
                ],
            },
        )
        assert oc_resp.status_code == 201, oc_resp.text
        return oc_resp.json()

    oc_1 = await _crear_oc("OC-LEC-001", [{"almacen_id": 1, "cantidad_distribuida": 10}])
    oc_2 = await _crear_oc("OC-LEC-002", [{"almacen_id": 2, "cantidad_distribuida": 10}])
    oc_any = await _crear_oc(
        "OC-LEC-003", [{"almacen_id": 1, "cantidad_distribuida": 5}, {"almacen_id": 2, "cantidad_distribuida": 5}]
    )

    pedido_1_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": oc_1["orden_compra_id"],
            "menu_id": ctx["menu_id"],
            "almacen_id": 1,
            "semana_inicio": date.today().isoformat(),
            "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido_1_resp.status_code == 201, pedido_1_resp.text
    pedido_2_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": oc_2["orden_compra_id"],
            "menu_id": ctx["menu_id"],
            "almacen_id": 2,
            "semana_inicio": date.today().isoformat(),
            "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
        },
    )
    assert pedido_2_resp.status_code == 201, pedido_2_resp.text

    guia_1_resp = await client.post(
        "/api/v1/guias-remision",
        headers=headers,
        json={
            "numero_guia": "GR-LEC-001",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": oc_1["orden_compra_id"],
            "pedido_semanal_id": pedido_1_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": oc_1["detalle"][0]["orden_compra_detalle_id"], "cantidad_entregada": 1}],
        },
    )
    assert guia_1_resp.status_code == 201, guia_1_resp.text
    guia_2_resp = await client.post(
        "/api/v1/guias-remision",
        headers=headers,
        json={
            "numero_guia": "GR-LEC-002",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": oc_2["orden_compra_id"],
            "pedido_semanal_id": pedido_2_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 2,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": oc_2["detalle"][0]["orden_compra_detalle_id"], "cantidad_entregada": 1}],
        },
    )
    assert guia_2_resp.status_code == 201, guia_2_resp.text

    headers_restringido = _headers_rol("LOGISTICA_CENTRAL", almacenes=[1])

    # ---------------------------------------------------------- órdenes de compra
    lista_oc = await client.get("/api/v1/ordenes-compra", headers=headers_restringido)
    assert lista_oc.status_code == 200, lista_oc.text
    numeros_oc = {o["numero_oc"] for o in lista_oc.json()["items"]}
    assert numeros_oc == {"OC-LEC-001", "OC-LEC-003"}  # OC-LEC-002 (solo almacén 2) queda fuera

    assert (await client.get(f"/api/v1/ordenes-compra/{oc_1['orden_compra_id']}", headers=headers_restringido)).status_code == 200
    assert (await client.get(f"/api/v1/ordenes-compra/{oc_2['orden_compra_id']}", headers=headers_restringido)).status_code == 403
    # política ANY: acceso a almacén 1 basta para ver una OC distribuida también al 2
    assert (await client.get(f"/api/v1/ordenes-compra/{oc_any['orden_compra_id']}", headers=headers_restringido)).status_code == 200

    # ------------------------------------------------------------ pedidos semanales
    lista_pedidos = await client.get("/api/v1/pedidos-semanales", headers=headers_restringido)
    assert lista_pedidos.status_code == 200, lista_pedidos.text
    assert len(lista_pedidos.json()["items"]) == 1
    assert lista_pedidos.json()["items"][0]["pedido_semanal_id"] == pedido_1_resp.json()["pedido_semanal_id"]

    assert (
        await client.get(f"/api/v1/pedidos-semanales/{pedido_1_resp.json()['pedido_semanal_id']}", headers=headers_restringido)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/pedidos-semanales/{pedido_2_resp.json()['pedido_semanal_id']}", headers=headers_restringido)
    ).status_code == 403

    # -------------------------------------------------------------- guías de remisión
    lista_guias = await client.get("/api/v1/guias-remision", headers=headers_restringido)
    assert lista_guias.status_code == 200, lista_guias.text
    assert {g["numero_guia"] for g in lista_guias.json()["items"]} == {"GR-LEC-001"}

    guia_1_id = guia_1_resp.json()["guia_remision_id"]
    guia_2_id = guia_2_resp.json()["guia_remision_id"]
    assert (await client.get(f"/api/v1/guias-remision/{guia_1_id}", headers=headers_restringido)).status_code == 200
    assert (await client.get(f"/api/v1/guias-remision/{guia_2_id}", headers=headers_restringido)).status_code == 403

    # regresión: ADMIN sigue viendo todo
    lista_oc_admin = await client.get("/api/v1/ordenes-compra", headers=headers)
    assert {o["numero_oc"] for o in lista_oc_admin.json()["items"]} == {"OC-LEC-001", "OC-LEC-002", "OC-LEC-003"}


@pytest.mark.asyncio
async def test_rn_alcance_proveedor_pedidos_semanales(client: AsyncClient):
    """Sesión 16: pedidos_semanales.py quedó fuera del alcance de PROVEEDOR
    en la Sesión 12 porque PedidoSemanal no tiene proveedor_id directo — se
    deriva vía orden_compra -> contrato.proveedor_id."""
    headers = _headers_admin()
    ctx_a = await _preparar_contrato_con_producto(
        client,
        headers,
        producto_codigo="P-PED-A",
        proveedor_ruc="20333333333",
        proveedor_razon_social="Proveedor Pedidos A",
        numero_contrato="CTR-PED-A",
    )
    ctx_b = await _preparar_contrato_con_producto(
        client,
        headers,
        producto_codigo="P-PED-B",
        proveedor_ruc="20444444444",
        proveedor_razon_social="Proveedor Pedidos B",
        numero_contrato="CTR-PED-B",
    )

    async def _crear_pedido(ctx: dict, numero_oc: str) -> dict:
        oc_resp = await client.post(
            "/api/v1/ordenes-compra",
            headers=headers,
            json={
                "numero_oc": numero_oc,
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
        assert oc_resp.status_code == 201, oc_resp.text
        oc = oc_resp.json()

        pedido_resp = await client.post(
            "/api/v1/pedidos-semanales",
            headers=headers,
            json={
                "orden_compra_id": oc["orden_compra_id"],
                "menu_id": ctx["menu_id"],
                "almacen_id": 1,
                "semana_inicio": date.today().isoformat(),
                "semana_fin": (date.today() + timedelta(days=6)).isoformat(),
            },
        )
        assert pedido_resp.status_code == 201, pedido_resp.text
        return pedido_resp.json()

    pedido_a = await _crear_pedido(ctx_a, "OC-PED-A-001")
    pedido_b = await _crear_pedido(ctx_b, "OC-PED-B-001")

    headers_proveedor_a = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=ctx_a["proveedor_id"])

    lista = await client.get("/api/v1/pedidos-semanales", headers=headers_proveedor_a)
    assert lista.status_code == 200, lista.text
    assert {p["pedido_semanal_id"] for p in lista.json()["items"]} == {pedido_a["pedido_semanal_id"]}

    detalle_propio = await client.get(f"/api/v1/pedidos-semanales/{pedido_a['pedido_semanal_id']}", headers=headers_proveedor_a)
    assert detalle_propio.status_code == 200, detalle_propio.text

    detalle_ajeno = await client.get(f"/api/v1/pedidos-semanales/{pedido_b['pedido_semanal_id']}", headers=headers_proveedor_a)
    assert detalle_ajeno.status_code == 403


@pytest.mark.asyncio
async def test_cierre_mensual(client: AsyncClient):
    """RN-10 (Sesión 20): gate informativo, sin efectos secundarios —
    bloquea (listo_para_cierre=False) mientras alguna OC del periodo siga
    sin llegar a un estado terminal, y la lista."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    periodo = date.today().replace(day=1)
    oc_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-CIERRE-001",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": periodo.isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 10,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 10}],
                }
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    orden_compra_id = oc_resp.json()["orden_compra_id"]

    estado_antes = await client.get(
        f"/api/v1/ordenes-compra/cierre-mensual?anio={periodo.year}&mes={periodo.month}", headers=headers
    )
    assert estado_antes.status_code == 200, estado_antes.text
    body_antes = estado_antes.json()
    assert body_antes["listo_para_cierre"] is False
    assert any(oc["orden_compra_id"] == orden_compra_id for oc in body_antes["ordenes_pendientes"])

    anular = await client.patch(
        f"/api/v1/ordenes-compra/{orden_compra_id}/estado", headers=headers, json={"estado": "ANULADA"}
    )
    assert anular.status_code == 200, anular.text

    estado_despues = await client.get(
        f"/api/v1/ordenes-compra/cierre-mensual?anio={periodo.year}&mes={periodo.month}", headers=headers
    )
    assert estado_despues.status_code == 200, estado_despues.text
    assert estado_despues.json()["listo_para_cierre"] is True
    assert estado_despues.json()["ordenes_pendientes"] == []
