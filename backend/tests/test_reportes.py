"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica los 3 reportes transversales: valorización de inventario,
comparativo consumo teórico (BOM, Módulo 1A) vs. comprado (Módulo 3) vs.
recibido (Almacén) vs. despachado (Módulo 4), y alertas por almacén (stock
bajo, próximos a vencer, observaciones sin resolver).
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.test_cocina import _headers_admin, _ingresar_stock, _preparar_contrato_con_producto, client  # noqa: F401
from tests.test_inspeccion import _crear_guia_completa  # noqa: F401


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
    fecha_inicio = date.today().replace(day=1)
    fecha_fin = date.today()
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
