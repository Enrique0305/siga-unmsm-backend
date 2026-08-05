"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo del Módulo 4 — Cocina/Consumo: solicitud de cocina que
reserva stock_comprometido (RN-07/21) y calcula cantidad_teorica_bom desde
dosificacion_detalle (RN-24, ya calculado en Módulo 1A) -> nota de salida
que descuenta el almacén de la solicitud (RN-17), libera la reserva y
registra el movimiento real en kardex -> comparación consumo real vs.
teórico (variacion_pct) -> anulación de una solicitud sin despachar.

Este archivo arma su propio fixture `client` (en vez de reusar el de
tests.test_compras) porque necesita además `CategoriaAlimento` sembrada
para poder crear un `Alimento` y vincularlo a un `Producto` vía
`alimento_id` — algo que los otros flujos no necesitan.
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
from tests.test_inspeccion import _crear_guia_completa  # noqa: F401


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(bind=engine, expire_on_commit=False)

    from app.models.catalogos import CategoriaAlimento, UnidadMedida
    from app.models.organizacion import Almacen, CentroConsumo, Sede

    async with TestSession() as seed_session:
        seed_session.add(UnidadMedida(unidad_id=1, codigo="KG", nombre="Kilogramo"))
        seed_session.add(CategoriaAlimento(categoria_alimento_id=1, nombre="Cereales"))
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
        # Expuesto para tests que necesitan una sesión cruda contra el mismo
        # engine en memoria (ej. sembrar una sede/almacén adicional fuera del
        # flujo HTTP) — mismo patrón que tests.test_compras.client.
        ac.session_factory = TestSession  # type: ignore[attr-defined]
        yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


def _headers_admin() -> dict:
    token = create_access_token(usuario_id=1, rol="ADMIN", almacenes=[], acceso_todos_almacenes=True)
    return {"Authorization": f"Bearer {token}"}


def _headers_rol(rol: str, almacenes: list[int]) -> dict:
    token = create_access_token(usuario_id=3, rol=rol, almacenes=almacenes, acceso_todos_almacenes=False)
    return {"Authorization": f"Bearer {token}"}


async def _preparar_contrato_con_producto(client: AsyncClient, headers: dict, alimento_id: int | None = None) -> dict:
    """Igual que tests.test_compras._preparar_contrato_con_producto, pero
    permite vincular el producto a un alimento (para poblar cantidad_teorica_bom)."""
    producto_json = {"codigo": "P001", "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1}
    if alimento_id is not None:
        producto_json["alimento_id"] = alimento_id
    producto_resp = await client.post("/api/v1/productos", headers=headers, json=producto_json)
    assert producto_resp.status_code == 201, producto_resp.text
    producto_id = producto_resp.json()["producto_id"]

    racion_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2026, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    assert racion_resp.status_code == 201, racion_resp.text
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


async def _ingresar_stock(client: AsyncClient, headers: dict, guia_ctx: dict, cantidad: float) -> None:
    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"], "cantidad_conforme": cantidad, "cantidad_observada": 0}
            ],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    inspeccion_detalle_id = inspeccion_resp.json()["detalle"][0]["inspeccion_detalle_id"]

    ingreso_resp = await client.post(
        "/api/v1/ingresos-almacen",
        headers=headers,
        json={
            "numero_ingreso": f"ING-{guia_ctx['guia_remision_id']}",
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [{"inspeccion_detalle_id": inspeccion_detalle_id, "cantidad_ingresada": cantidad}],
        },
    )
    assert ingreso_resp.status_code == 201, ingreso_resp.text


@pytest.mark.asyncio
async def test_flujo_cocina_completo(client: AsyncClient):
    headers = _headers_admin()

    # 1) alimento + producto vinculado (para poblar cantidad_teorica_bom)
    alimento_resp = await client.post(
        "/api/v1/alimentos",
        headers=headers,
        json={
            "codigo": "A001",
            "nombre": "Arroz superior",
            "categoria_alimento_id": 1,
            "tipo": "BASE_TABLA",
            "fuente": "Test",
            "valores": {"energia_kcal": 350, "proteinas_g": 7},
        },
    )
    assert alimento_resp.status_code == 201, alimento_resp.text
    alimento_id = alimento_resp.json()["alimento_id"]

    ctx = await _preparar_contrato_con_producto(client, headers, alimento_id=alimento_id)
    producto_id = ctx["producto_id"]

    guia_ctx = await _crear_guia_completa(client, headers, ctx, "OC-COC-001", "GR-COC-001", cantidad=40)
    await _ingresar_stock(client, headers, guia_ctx, cantidad=40)

    # 2) receta VIGENTE con ese alimento como ingrediente
    receta_resp = await client.post(
        "/api/v1/recetas",
        headers=headers,
        json={
            "codigo": "REC-001",
            "nombre": "Arroz con pollo",
            "categoria_preparacion": "SEGUNDO",
            "numero_raciones_base": 100,
            "tamano_porcion_g": 250,
            "rendimiento_pct": 90,
            "ingredientes": [{"alimento_id": alimento_id, "cantidad_bruta_g": 18, "cantidad_neta_g": 17, "unidad_id": 1, "merma_pct": 4}],
        },
    )
    assert receta_resp.status_code == 201, receta_resp.text
    receta_id = receta_resp.json()["receta_id"]
    for estado in ("EN_REVISION", "APROBADO", "VIGENTE"):
        r = await client.patch(f"/api/v1/recetas/{receta_id}/estado", headers=headers, json={"estado": estado})
        assert r.status_code == 200, r.text

    # 3) menú del día + plato + dosificación (BOM ya calculado en Módulo 1A)
    dia_resp = await client.post(
        f"/api/v1/planificacion/menus-quincenales/{ctx['menu_id']}/dias",
        headers=headers,
        json={"fecha": date.today().isoformat(), "tipo_servicio": "ALMUERZO", "raciones_programadas": 100},
    )
    assert dia_resp.status_code == 201, dia_resp.text
    menu_dia_id = dia_resp.json()["menu_dia_id"]

    plato_resp = await client.post(
        f"/api/v1/planificacion/dias/{menu_dia_id}/platos", headers=headers, json={"receta_id": receta_id}
    )
    assert plato_resp.status_code == 201, plato_resp.text

    dosificacion_resp = await client.post(
        f"/api/v1/planificacion/dias/{menu_dia_id}/dosificacion",
        headers=headers,
        params={"centro_consumo_id": 1},
    )
    assert dosificacion_resp.status_code == 200, dosificacion_resp.text
    assert len(dosificacion_resp.json()) > 0

    # 4) RN-20: un cocinero sin acceso al almacén 1 no puede solicitar sobre él
    solicitud_bloqueada_rn20 = await client.post(
        "/api/v1/solicitudes-cocina",
        headers=_headers_rol("COCINA", almacenes=[999]),
        json={
            "numero_solicitud": "SOL-0001",
            "centro_consumo_id": 1,
            "menu_dia_id": menu_dia_id,
            "detalle": [{"producto_id": producto_id, "cantidad_solicitada": 15}],
        },
    )
    assert solicitud_bloqueada_rn20.status_code == 403

    # 5) solicitud válida: reserva stock_comprometido y calcula el teórico
    solicitud_resp = await client.post(
        "/api/v1/solicitudes-cocina",
        headers=headers,
        json={
            "numero_solicitud": "SOL-0001",
            "centro_consumo_id": 1,
            "menu_dia_id": menu_dia_id,
            "detalle": [{"producto_id": producto_id, "cantidad_solicitada": 15}],
        },
    )
    assert solicitud_resp.status_code == 201, solicitud_resp.text
    solicitud = solicitud_resp.json()
    assert solicitud["estado"] == "PENDIENTE"
    linea_solicitud = solicitud["detalle"][0]
    assert linea_solicitud["cantidad_teorica_bom"] is not None
    assert linea_solicitud["cantidad_teorica_bom"] > 0
    solicitud_id = solicitud["solicitud_cocina_id"]
    solicitud_detalle_id = linea_solicitud["solicitud_cocina_detalle_id"]

    stock_resp = await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    stock = stock_resp.json()["items"][0]
    assert stock["stock_fisico"] == pytest.approx(40.0)
    assert stock["stock_comprometido"] == pytest.approx(15.0)
    assert stock["stock_disponible"] == pytest.approx(25.0)

    # 6) RN-07: otra solicitud que excede lo disponible (25) queda bloqueada
    solicitud_excedida = await client.post(
        "/api/v1/solicitudes-cocina",
        headers=headers,
        json={
            "numero_solicitud": "SOL-0002",
            "centro_consumo_id": 1,
            "menu_dia_id": menu_dia_id,
            "detalle": [{"producto_id": producto_id, "cantidad_solicitada": 30}],
        },
    )
    assert solicitud_excedida.status_code == 422
    assert "RN-07" in solicitud_excedida.json()["detail"]

    # 7) nota de salida que no cubre la línea de la solicitud -> bloqueada
    nota_incompleta = await client.post(
        "/api/v1/notas-salida",
        headers=headers,
        json={"numero_nota": "NS-0001", "solicitud_cocina_id": solicitud_id, "detalle": [{"solicitud_cocina_detalle_id": 999, "cantidad_despachada": 15}]},
    )
    assert nota_incompleta.status_code == 422

    # 8) nota de salida completa: libera comprometido, descuenta físico, valoriza
    nota_resp = await client.post(
        "/api/v1/notas-salida",
        headers=headers,
        json={
            "numero_nota": "NS-0001",
            "solicitud_cocina_id": solicitud_id,
            "detalle": [{"solicitud_cocina_detalle_id": solicitud_detalle_id, "cantidad_despachada": 15}],
        },
    )
    assert nota_resp.status_code == 201, nota_resp.text
    nota = nota_resp.json()
    linea_nota = nota["detalle"][0]
    assert linea_nota["costo_unitario"] == pytest.approx(5.5)
    assert linea_nota["variacion_pct"] is not None  # 15 despachado vs. teórico calculado

    stock_tras_despacho = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_tras_despacho["stock_fisico"] == pytest.approx(25.0)  # 40 - 15
    assert stock_tras_despacho["stock_comprometido"] == pytest.approx(0.0)

    solicitud_tras_despacho = (await client.get(f"/api/v1/solicitudes-cocina/{solicitud_id}", headers=headers)).json()
    assert solicitud_tras_despacho["estado"] == "DESPACHADA"

    # 9) no se puede anular una solicitud ya despachada
    anular_bloqueado = await client.patch(
        f"/api/v1/solicitudes-cocina/{solicitud_id}/estado", headers=headers, json={"estado": "ANULADA"}
    )
    assert anular_bloqueado.status_code == 422

    # 10) una segunda solicitud sin despachar sí se puede anular, liberando la reserva
    solicitud_2 = await client.post(
        "/api/v1/solicitudes-cocina",
        headers=headers,
        json={
            "numero_solicitud": "SOL-0003",
            "centro_consumo_id": 1,
            "menu_dia_id": menu_dia_id,
            "detalle": [{"producto_id": producto_id, "cantidad_solicitada": 5}],
        },
    )
    assert solicitud_2.status_code == 201, solicitud_2.text
    solicitud_2_id = solicitud_2.json()["solicitud_cocina_id"]

    stock_con_reserva_2 = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_con_reserva_2["stock_comprometido"] == pytest.approx(5.0)

    anular_ok = await client.patch(
        f"/api/v1/solicitudes-cocina/{solicitud_2_id}/estado", headers=headers, json={"estado": "ANULADA"}
    )
    assert anular_ok.status_code == 200, anular_ok.text
    assert anular_ok.json()["estado"] == "ANULADA"

    stock_final = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_final["stock_comprometido"] == pytest.approx(0.0)
