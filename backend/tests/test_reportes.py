"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica los 3 reportes transversales: valorización de inventario,
comparativo consumo teórico (BOM, Módulo 1A) vs. comprado (Módulo 3) vs.
recibido (Almacén) vs. despachado (Módulo 4), y alertas por almacén (stock
bajo, próximos a vencer, observaciones sin resolver).
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from tests.test_cocina import _headers_admin, _ingresar_stock, _preparar_contrato_con_producto, client  # noqa: F401
from tests.test_inspeccion import _crear_guia_completa  # noqa: F401


def _headers_rol(rol: str) -> dict:
    token = create_access_token(usuario_id=3, rol=rol, almacenes=[], acceso_todos_almacenes=(rol == "LOGISTICA_CENTRAL"))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_reportes_completo(client: AsyncClient):
    headers = _headers_admin()

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

    # línea con lote próximo a vencer (10 días), 40 unidades, 100% conforme
    guia_1 = await _crear_guia_completa(
        client, headers, ctx, "OC-REP-001", "GR-REP-001", cantidad=40, semana_offset_dias=0,
        fecha_vencimiento=date.today() + timedelta(days=10),
    )
    await _ingresar_stock(client, headers, guia_1, cantidad=40)

    # -------------------------------------------------------- valorización
    valorizacion_resp = await client.get(
        "/api/v1/reportes/valorizacion-inventario", headers=headers, params={"almacen_id": 1}
    )
    assert valorizacion_resp.status_code == 200, valorizacion_resp.text
    valorizacion = valorizacion_resp.json()[0]
    assert valorizacion["almacen_id"] == 1
    assert valorizacion["valor_valorizado_total"] == pytest.approx(40 * 5.5)

    # stock_minimo_referencial para forzar la alerta de stock bajo más adelante
    patch_producto = await client.patch(f"/api/v1/productos/{producto_id}", headers=headers, json={"stock_minimo_referencial": 30})
    assert patch_producto.status_code == 200, patch_producto.text

    # -------------------------------------------- receta + dosificación (BOM)
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
        f"/api/v1/planificacion/dias/{menu_dia_id}/dosificacion", headers=headers, params={"centro_consumo_id": 1}
    )
    assert dosificacion_resp.status_code == 200, dosificacion_resp.text

    # ------------------------------------------- solicitud + despacho (consumo real)
    solicitud_resp = await client.post(
        "/api/v1/solicitudes-cocina",
        headers=headers,
        json={
            "numero_solicitud": "SOL-REP-001",
            "centro_consumo_id": 1,
            "menu_dia_id": menu_dia_id,
            "detalle": [{"producto_id": producto_id, "cantidad_solicitada": 15}],
        },
    )
    assert solicitud_resp.status_code == 201, solicitud_resp.text
    solicitud = solicitud_resp.json()
    solicitud_id = solicitud["solicitud_cocina_id"]
    solicitud_detalle_id = solicitud["detalle"][0]["solicitud_cocina_detalle_id"]

    nota_resp = await client.post(
        "/api/v1/notas-salida",
        headers=headers,
        json={
            "numero_nota": "NS-REP-001",
            "solicitud_cocina_id": solicitud_id,
            "detalle": [{"solicitud_cocina_detalle_id": solicitud_detalle_id, "cantidad_despachada": 15}],
        },
    )
    assert nota_resp.status_code == 201, nota_resp.text

    # ---------------------------------------------------- comparativo consumo
    # IngresoAlmacen.fecha_ingreso / NotaSalida.fecha_salida se fijan con
    # server_default=func.now(), que en SQLite es siempre UTC — comparar
    # contra date.today() (hora local) es la fragilidad ya documentada en
    # CLAUDE.md: si el entorno corre justo alrededor de medianoche UTC, el
    # día local y el día UTC difieren y la fila recién insertada queda
    # fuera de la ventana. Se ancla la ventana a la fecha UTC actual, el
    # mismo reloj que usa la base, para que la comparación sea consistente
    # sin importar la zona horaria del host.
    hoy_utc = datetime.now(timezone.utc).date()
    fecha_inicio = hoy_utc.replace(day=1)
    fecha_fin = hoy_utc
    comparativo_resp = await client.get(
        "/api/v1/reportes/comparativo-consumo",
        headers=headers,
        params={"producto_id": producto_id, "fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )
    assert comparativo_resp.status_code == 200, comparativo_resp.text
    comparativo = comparativo_resp.json()
    assert comparativo["cantidad_teorica"] > 0
    assert comparativo["cantidad_comprada"] == pytest.approx(40.0)
    assert comparativo["cantidad_recibida"] == pytest.approx(40.0)
    assert comparativo["cantidad_despachada"] == pytest.approx(15.0)

    # producto inexistente -> 404
    comparativo_404 = await client.get(
        "/api/v1/reportes/comparativo-consumo",
        headers=headers,
        params={"producto_id": 999999, "fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )
    assert comparativo_404.status_code == 404

    # ------------------------------------------ segunda guía: OBSERVADO sin acta
    guia_2 = await _crear_guia_completa(client, headers, ctx, "OC-REP-002", "GR-REP-002", cantidad=10, semana_offset_dias=7)
    inspeccion_2 = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_2["guia_remision_id"],
            "detalle": [{"guia_remision_detalle_id": guia_2["guia_remision_detalle_id"], "cantidad_conforme": 8, "cantidad_observada": 2}],
        },
    )
    assert inspeccion_2.status_code == 201, inspeccion_2.text

    # ------------------------------------------------------------- alertas
    alertas_resp = await client.get("/api/v1/reportes/alertas", headers=headers, params={"almacen_id": 1, "dias_vencimiento": 30})
    assert alertas_resp.status_code == 200, alertas_resp.text
    alertas = alertas_resp.json()

    assert len(alertas["stock_bajo"]) == 1
    assert alertas["stock_bajo"][0]["producto_id"] == producto_id
    assert alertas["stock_bajo"][0]["stock_fisico"] == pytest.approx(25.0)  # 40 ingresado - 15 despachado

    assert len(alertas["proximos_vencer"]) == 1
    assert alertas["proximos_vencer"][0]["producto_id"] == producto_id
    assert alertas["proximos_vencer"][0]["cantidad_ingresada"] == pytest.approx(40.0)

    assert len(alertas["observaciones_sin_resolver"]) == 1
    obs = alertas["observaciones_sin_resolver"][0]
    assert obs["guia_remision_id"] == guia_2["guia_remision_id"]
    assert obs["cantidad_observada"] == pytest.approx(2.0)
    assert obs["acta_estado"] is None


@pytest.mark.asyncio
async def test_reportes_requiere_rol_autorizado(client: AsyncClient):
    """Los 3 reportes son agregados de todo el sistema — el gate de
    frontend/lib/nav.ts (ADMIN, LOGISTICA_CENTRAL) también debe cumplirse
    en el backend, no solo ocultarse en el sidebar."""
    sin_acceso = _headers_rol("COCINA")
    con_acceso = _headers_rol("LOGISTICA_CENTRAL")

    for path, params in (
        ("/api/v1/reportes/valorizacion-inventario", {}),
        ("/api/v1/reportes/comparativo-consumo", {"producto_id": 1, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}),
        ("/api/v1/reportes/alertas", {}),
    ):
        bloqueado = await client.get(path, headers=sin_acceso, params=params)
        assert bloqueado.status_code == 403, bloqueado.text

        permitido = await client.get(path, headers=con_acceso, params=params)
        assert permitido.status_code in (200, 404), permitido.text


@pytest.mark.asyncio
async def test_parametro_sistema_dias_vencimiento(client: AsyncClient):
    """Sesión 18: 'Parámetros del sistema' (09 Administración) — se conecta
    el umbral de días para "próximos a vencer" de /reportes/alertas, hoy
    hardcodeado en 30."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    # lote que vence en 10 días
    guia = await _crear_guia_completa(
        client, headers, ctx, "OC-PARAM-SIS", "GR-PARAM-SIS", cantidad=40,
        fecha_vencimiento=date.today() + timedelta(days=10),
    )
    await _ingresar_stock(client, headers, guia, cantidad=40)

    # sin parámetro configurado: default 30 -> el lote (10 días) aparece
    alertas_default = await client.get("/api/v1/reportes/alertas", headers=headers)
    assert alertas_default.status_code == 200, alertas_default.text
    assert len(alertas_default.json()["proximos_vencer"]) == 1

    # GET es lectura abierta (ADMIN/LOGISTICA_CENTRAL, ya cubierto por
    # ROLES_LECTURA de reportes.py); PUT/DELETE de parametros-sistema
    # exigen ADMIN estrictamente, ni LOGISTICA_CENTRAL
    headers_logistica = _headers_rol("LOGISTICA_CENTRAL")
    put_bloqueado = await client.put(
        "/api/v1/parametros-sistema",
        headers=headers_logistica,
        json={"clave": "alertas_dias_vencimiento", "valor": "5"},
    )
    assert put_bloqueado.status_code == 403, put_bloqueado.text

    put_resp = await client.put(
        "/api/v1/parametros-sistema",
        headers=headers,
        json={"clave": "alertas_dias_vencimiento", "valor": "5", "descripcion": "Ventana de vencimiento de alertas"},
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["valor"] == "5"

    # ahora el default es 5 -> el lote (10 días) ya no aparece sin query param
    alertas_con_parametro = await client.get("/api/v1/reportes/alertas", headers=headers)
    assert alertas_con_parametro.status_code == 200, alertas_con_parametro.text
    assert alertas_con_parametro.json()["proximos_vencer"] == []

    # el query param explícito sigue pudiendo pisar el parámetro configurado
    alertas_override_explicito = await client.get(
        "/api/v1/reportes/alertas", headers=headers, params={"dias_vencimiento": 30}
    )
    assert len(alertas_override_explicito.json()["proximos_vencer"]) == 1

    lista = await client.get("/api/v1/parametros-sistema", headers=headers_logistica)
    assert lista.status_code == 200, lista.text
    assert any(p["clave"] == "alertas_dias_vencimiento" for p in lista.json())

    delete_bloqueado = await client.delete("/api/v1/parametros-sistema/alertas_dias_vencimiento", headers=headers_logistica)
    assert delete_bloqueado.status_code == 403

    delete_resp = await client.delete("/api/v1/parametros-sistema/alertas_dias_vencimiento", headers=headers)
    assert delete_resp.status_code == 204, delete_resp.text

    # eliminado el parámetro, vuelve al default de 30
    alertas_tras_eliminar = await client.get("/api/v1/reportes/alertas", headers=headers)
    assert len(alertas_tras_eliminar.json()["proximos_vencer"]) == 1
