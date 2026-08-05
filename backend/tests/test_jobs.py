"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Primer archivo de test que llama funciones de core/jobs.py directo con una
AsyncSession cruda (mismo engine que respalda el fixture `client`, expuesto
vía `client.session_factory`), ya que estos jobs no tienen -ni deben
tener- un endpoint HTTP que los dispare: los ejecuta APScheduler
(core/scheduler.py), no un usuario (Sesión 20, RN-11/RN-12).
"""
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401  registra los modelos
from app.core.jobs import procesar_actas_vencidas, procesar_alertas_contratos
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from tests.test_compras import _headers_admin, _preparar_contrato_con_producto


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
        await seed_session.flush()
        seed_session.add(CentroConsumo(centro_consumo_id=1, sede_id=1, almacen_id=1, nombre="Comedor Test"))
        await seed_session.commit()

    async def _get_db_override():
        async with TestSession() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _get_db_override

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Ver el docstring del módulo: expuesto para que los tests de este
        # archivo abran su propia sesión cruda contra el mismo engine.
        ac.session_factory = TestSession  # type: ignore[attr-defined]
        yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


async def _crear_oc_dos_lineas(client: AsyncClient, headers: dict, ctx: dict) -> dict:
    """OC con 2 líneas OBSERVADO sobre el mismo contrato — para probar el
    caso "una acta vence, la otra no" de procesar_actas_vencidas."""
    producto2_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P002-JOB", "nombre": "Aceite", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert producto2_resp.status_code == 201, producto2_resp.text
    producto2_id = producto2_resp.json()["producto_id"]

    pc2_resp = await client.post(
        f"/api/v1/contratos/{ctx['contrato_id']}/productos",
        headers=headers,
        json={"producto_id": producto2_id, "precio_unitario": 3.0, "cantidad_contratada": 100},
    )
    assert pc2_resp.status_code == 201, pc2_resp.text
    producto_contratado2_id = pc2_resp.json()["producto_contratado_id"]

    oc_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-JOB-002LINEAS",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 40,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 40}],
                },
                {
                    "producto_contratado_id": producto_contratado2_id,
                    "cantidad_solicitada": 20,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 20}],
                },
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    oc = oc_resp.json()
    orden_compra_id = oc["orden_compra_id"]
    ocd1 = oc["detalle"][0]["orden_compra_detalle_id"]
    ocd2 = oc["detalle"][1]["orden_compra_detalle_id"]

    pedido_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": orden_compra_id,
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
            "numero_guia": "GR-JOB-002LINEAS",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": pedido_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [
                {"orden_compra_detalle_id": ocd1, "cantidad_entregada": 40},
                {"orden_compra_detalle_id": ocd2, "cantidad_entregada": 20},
            ],
        },
    )
    assert guia_resp.status_code == 201, guia_resp.text
    guia = guia_resp.json()

    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia["guia_remision_id"],
            "detalle": [
                {
                    "guia_remision_detalle_id": guia["detalle"][0]["guia_remision_detalle_id"],
                    "cantidad_conforme": 0,
                    "cantidad_observada": 40,
                },
                {
                    "guia_remision_detalle_id": guia["detalle"][1]["guia_remision_detalle_id"],
                    "cantidad_conforme": 0,
                    "cantidad_observada": 20,
                },
            ],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    detalle = inspeccion_resp.json()["detalle"]
    return {
        "orden_compra_id": orden_compra_id,
        "inspeccion_detalle_id_1": detalle[0]["inspeccion_detalle_id"],
        "inspeccion_detalle_id_2": detalle[1]["inspeccion_detalle_id"],
    }


@pytest.mark.asyncio
async def test_procesar_actas_vencidas_cierra_oc_y_penaliza(client: AsyncClient):
    """RN-11: una única línea OBSERVADO cuya acta ya venció -> el job la
    rechaza, cierra la OC sola (PENALIZADO, con Penalidad automática) y la
    guía pasa a SUBSANADO — sin ninguna acción de un usuario."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    oc_resp = await client.post(
        "/api/v1/ordenes-compra",
        headers=headers,
        json={
            "numero_oc": "OC-JOB-001",
            "contrato_id": ctx["contrato_id"],
            "periodo_mes": date.today().replace(day=1).isoformat(),
            "detalle": [
                {
                    "producto_contratado_id": ctx["producto_contratado_id"],
                    "cantidad_solicitada": 40,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": 40}],
                }
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    oc = oc_resp.json()
    orden_compra_id = oc["orden_compra_id"]
    ocd1 = oc["detalle"][0]["orden_compra_detalle_id"]

    pedido_resp = await client.post(
        "/api/v1/pedidos-semanales",
        headers=headers,
        json={
            "orden_compra_id": orden_compra_id,
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
            "numero_guia": "GR-JOB-001",
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": pedido_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [{"orden_compra_detalle_id": ocd1, "cantidad_entregada": 40}],
        },
    )
    assert guia_resp.status_code == 201, guia_resp.text
    guia = guia_resp.json()
    guia_remision_id = guia["guia_remision_id"]

    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_remision_id,
            "detalle": [
                {
                    "guia_remision_detalle_id": guia["detalle"][0]["guia_remision_detalle_id"],
                    "cantidad_conforme": 0,
                    "cantidad_observada": 40,
                }
            ],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    inspeccion_detalle_id = inspeccion_resp.json()["detalle"][0]["inspeccion_detalle_id"]

    acta_resp = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id}",
        headers=headers,
        json={
            "numero_acta": "ACTA-JOB-001",
            "motivo": "Merma en tránsito",
            "plazo_subsanacion": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert acta_resp.status_code == 201, acta_resp.text
    acta_id = acta_resp.json()["acta_observacion_id"]
    assert acta_resp.json()["plazo_vencido"] is True

    async with client.session_factory() as db:
        resultado = await procesar_actas_vencidas(db)
        await db.commit()
    assert resultado == {"actas_vencidas": 1, "ordenes_cerradas": 1}

    acta_final = await client.get(f"/api/v1/actas-observacion/{acta_id}", headers=headers)
    assert acta_final.json()["estado"] == "RECHAZADA"

    guia_final = await client.get(f"/api/v1/guias-remision/{guia_remision_id}", headers=headers)
    assert guia_final.json()["estado"] == "SUBSANADO"

    oc_final = await client.get(f"/api/v1/ordenes-compra/{orden_compra_id}", headers=headers)
    assert oc_final.json()["estado"] == "PENALIZADO"

    penalidades = await client.get(
        f"/api/v1/penalidades?orden_compra_id={orden_compra_id}", headers=headers
    )
    assert penalidades.status_code == 200, penalidades.text
    assert penalidades.json()["total"] == 1
    assert penalidades.json()["items"][0]["acta_observacion_id"] == acta_id

    # RN-08: la mutación automática sí queda auditada (current_usuario_id
    # se fijó al responsable_id de la OC durante el job).
    auditoria = await client.get(
        f"/api/v1/auditoria?entidad=orden_compra&entidad_id={orden_compra_id}", headers=headers
    )
    assert auditoria.status_code == 200, auditoria.text
    assert auditoria.json()["total"] >= 1


@pytest.mark.asyncio
async def test_procesar_actas_vencidas_no_cierra_con_otra_acta_pendiente(client: AsyncClient):
    """RN-11: si a la OC todavía le queda otra línea OBSERVADO con acta
    ABIERTA y no vencida, el job no fuerza el cierre — se deja para un día
    futuro, sin excepción no controlada."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    datos = await _crear_oc_dos_lineas(client, headers, ctx)

    acta1_resp = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{datos['inspeccion_detalle_id_1']}",
        headers=headers,
        json={
            "numero_acta": "ACTA-JOB-VENCIDA",
            "motivo": "Merma",
            "plazo_subsanacion": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert acta1_resp.status_code == 201, acta1_resp.text

    acta2_resp = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{datos['inspeccion_detalle_id_2']}",
        headers=headers,
        json={
            "numero_acta": "ACTA-JOB-VIGENTE",
            "motivo": "Lote incompleto",
            "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert acta2_resp.status_code == 201, acta2_resp.text
    acta2_id = acta2_resp.json()["acta_observacion_id"]

    async with client.session_factory() as db:
        resultado = await procesar_actas_vencidas(db)
        await db.commit()
    assert resultado == {"actas_vencidas": 1, "ordenes_cerradas": 0}

    acta2_final = await client.get(f"/api/v1/actas-observacion/{acta2_id}", headers=headers)
    assert acta2_final.json()["estado"] == "ABIERTA"

    oc_final = await client.get(f"/api/v1/ordenes-compra/{datos['orden_compra_id']}", headers=headers)
    assert oc_final.json()["estado"] == "EMITIDA"


@pytest.mark.asyncio
async def test_procesar_alertas_contratos(client: AsyncClient):
    """RN-12: alerta de vigencia + saldo -> Notificacion; sin cambios, no
    se duplica; al marcar leída, la siguiente corrida sí vuelve a crear una
    (la alerta sigue activa)."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    # fecha_fin por defecto = hoy + 200 días; saldo_fisico por defecto = 100%
    # (ninguno de los dos alerta con los umbrales por defecto, 30/15) — se
    # sube el umbral para forzar ambas alertas sin tocar el helper.
    put1 = await client.put(
        "/api/v1/parametros-sistema",
        headers=headers,
        json={"clave": "contratos_dias_alerta_vigencia", "valor": "250"},
    )
    assert put1.status_code == 200, put1.text
    put2 = await client.put(
        "/api/v1/parametros-sistema",
        headers=headers,
        json={"clave": "contratos_pct_alerta_saldo", "valor": "100"},
    )
    assert put2.status_code == 200, put2.text

    async with client.session_factory() as db:
        resultado = await procesar_alertas_contratos(db)
        await db.commit()
    assert resultado == {"notificaciones_creadas": 2}

    notifs = await client.get("/api/v1/notificaciones", headers=headers)
    assert notifs.status_code == 200, notifs.text
    assert notifs.json()["total"] == 2
    tipos = {n["tipo"] for n in notifs.json()["items"]}
    assert tipos == {"CONTRATO_VIGENCIA", "CONTRATO_SALDO"}

    # correr de nuevo sin cambios -> dedup, no crea nada mientras sigan sin leerse
    async with client.session_factory() as db:
        resultado2 = await procesar_alertas_contratos(db)
        await db.commit()
    assert resultado2 == {"notificaciones_creadas": 0}
    notifs2 = await client.get("/api/v1/notificaciones", headers=headers)
    assert notifs2.json()["total"] == 2

    # marcar una leída -> la próxima corrida sí crea una nueva para esa alerta
    notificacion_id = notifs2.json()["items"][0]["notificacion_id"]
    marcar = await client.patch(f"/api/v1/notificaciones/{notificacion_id}/leida", headers=headers)
    assert marcar.status_code == 200, marcar.text
    assert marcar.json()["leida"] is True

    async with client.session_factory() as db:
        resultado3 = await procesar_alertas_contratos(db)
        await db.commit()
    assert resultado3 == {"notificaciones_creadas": 1}
    notifs3 = await client.get("/api/v1/notificaciones", headers=headers)
    assert notifs3.json()["total"] == 3
