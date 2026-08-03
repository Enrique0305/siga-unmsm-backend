"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo del Módulo 5 — Conformidad y Pagos: cerrar una OC
totalmente CONFORME (cierre limpio, sin retenciones ni penalidad) vs.
cerrar una OC con una línea OBSERVADO cuya subsanación fue RECHAZADA
(bloqueado mientras el acta sigue sin resolver; al resolverse, cierre con
penalidad automática y estado PENALIZADO) -> generar el Informe de
Conformidad para Pago sobre cada una (verifica montos conforme/retenido/
penalidad) -> transición completa del informe hasta PAGADO -> penalidad
manual bloqueada tras generar el informe.
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.test_compras import _headers_admin, _preparar_contrato_con_producto, client  # noqa: F401
from tests.test_inspeccion import _crear_guia_completa  # noqa: F401


@pytest.mark.asyncio
async def test_flujo_pagos_completo(client: AsyncClient):
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    # ---------------------------------------------------------------- OC-A
    # Totalmente CONFORME: cierre limpio, sin retenciones ni penalidad.
    guia_a = await _crear_guia_completa(client, headers, ctx, "OC-PAG-A", "GR-PAG-A", cantidad=20, semana_offset_dias=0)

    inspeccion_a = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_a["guia_remision_id"],
            "detalle": [{"guia_remision_detalle_id": guia_a["guia_remision_detalle_id"], "cantidad_conforme": 20, "cantidad_observada": 0}],
        },
    )
    assert inspeccion_a.status_code == 201, inspeccion_a.text

    cierre_a = await client.patch(
        f"/api/v1/ordenes-compra/{guia_a['orden_compra_id']}/estado", headers=headers, json={"estado": "CERRADO"}
    )
    assert cierre_a.status_code == 200, cierre_a.text
    assert cierre_a.json()["estado"] == "CERRADO"

    informe_a_resp = await client.post(
        "/api/v1/informes-conformidad-pago",
        headers=headers,
        json={"numero_informe": "INF-A-001", "orden_compra_id": guia_a["orden_compra_id"]},
    )
    assert informe_a_resp.status_code == 201, informe_a_resp.text
    informe_a = informe_a_resp.json()
    assert informe_a["monto_conforme_total"] == pytest.approx(20 * 5.5)
    assert informe_a["monto_retenido_total"] == pytest.approx(0.0)
    assert informe_a["monto_penalidad_total"] == pytest.approx(0.0)
    assert informe_a["detalle"][0]["cantidad_conforme"] == pytest.approx(20.0)

    # Regenerar el informe sobre la misma OC está bloqueado
    informe_a_dup = await client.post(
        "/api/v1/informes-conformidad-pago",
        headers=headers,
        json={"numero_informe": "INF-A-002", "orden_compra_id": guia_a["orden_compra_id"]},
    )
    assert informe_a_dup.status_code == 422

    # Penalidad manual bloqueada tras generar el informe de esa OC
    penalidad_bloqueada = await client.post(
        "/api/v1/penalidades",
        headers=headers,
        json={"orden_compra_id": guia_a["orden_compra_id"], "monto_penalidad": 10, "motivo": "Atraso"},
    )
    assert penalidad_bloqueada.status_code == 422

    # Transición completa del informe hasta PAGADO
    informe_a_id = informe_a["informe_id"]
    for estado in ("RECIBIDO", "EN_PROCESO_DE_PAGO", "PAGADO"):
        r = await client.patch(f"/api/v1/informes-conformidad-pago/{informe_a_id}/estado", headers=headers, json={"estado": estado})
        assert r.status_code == 200, r.text
    informe_a_final = r.json()
    assert informe_a_final["estado"] == "PAGADO"
    assert informe_a_final["fecha_pago"] is not None

    # ---------------------------------------------------------------- OC-B
    # Línea OBSERVADO -> acta -> subsanación RECHAZADA -> cierre con penalidad.
    guia_b = await _crear_guia_completa(client, headers, ctx, "OC-PAG-B", "GR-PAG-B", cantidad=20, semana_offset_dias=7)

    inspeccion_b = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_b["guia_remision_id"],
            "detalle": [{"guia_remision_detalle_id": guia_b["guia_remision_detalle_id"], "cantidad_conforme": 15, "cantidad_observada": 5}],
        },
    )
    assert inspeccion_b.status_code == 201, inspeccion_b.text
    inspeccion_detalle_id_b = inspeccion_b.json()["detalle"][0]["inspeccion_detalle_id"]

    # cierre bloqueado: la línea OBSERVADO todavía no tiene acta
    cierre_b_bloqueado_1 = await client.patch(
        f"/api/v1/ordenes-compra/{guia_b['orden_compra_id']}/estado", headers=headers, json={"estado": "CERRADO"}
    )
    assert cierre_b_bloqueado_1.status_code == 422

    acta_b = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id_b}",
        headers=headers,
        json={"numero_acta": "ACTA-PAG-001", "motivo": "Lote parcialmente vencido", "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat()},
    )
    assert acta_b.status_code == 201, acta_b.text
    acta_b_id = acta_b.json()["acta_observacion_id"]

    # cierre bloqueado: el acta sigue ABIERTA
    cierre_b_bloqueado_2 = await client.patch(
        f"/api/v1/ordenes-compra/{guia_b['orden_compra_id']}/estado", headers=headers, json={"estado": "CERRADO"}
    )
    assert cierre_b_bloqueado_2.status_code == 422

    subsanacion_b = await client.post(
        f"/api/v1/actas-observacion/{acta_b_id}/subsanaciones",
        headers=headers,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "Reemplazo de lote"},
    )
    assert subsanacion_b.status_code == 201, subsanacion_b.text
    subsanacion_b_id = subsanacion_b.json()["subsanacion_id"]

    reinspeccion_b = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_b_id}/reinspeccion",
        headers=headers,
        json={"resultado_reinspeccion": "NO_CONFORME"},
    )
    assert reinspeccion_b.status_code == 200, reinspeccion_b.text

    acta_b_final = await client.get(f"/api/v1/actas-observacion/{acta_b_id}", headers=headers)
    assert acta_b_final.json()["estado"] == "RECHAZADA"

    # ahora sí se puede cerrar: PENALIZADO, con penalidad automática
    cierre_b = await client.patch(
        f"/api/v1/ordenes-compra/{guia_b['orden_compra_id']}/estado", headers=headers, json={"estado": "CERRADO"}
    )
    assert cierre_b.status_code == 200, cierre_b.text
    assert cierre_b.json()["estado"] == "PENALIZADO"

    penalidades_b = await client.get("/api/v1/penalidades", headers=headers, params={"orden_compra_id": guia_b["orden_compra_id"]})
    penalidades_b_items = penalidades_b.json()["items"]
    assert len(penalidades_b_items) == 1
    assert penalidades_b_items[0]["monto_penalidad"] == pytest.approx(5 * 5.5)  # 5 unidades rechazadas x precio
    assert penalidades_b_items[0]["acta_observacion_id"] == acta_b_id

    informe_b_resp = await client.post(
        "/api/v1/informes-conformidad-pago",
        headers=headers,
        json={"numero_informe": "INF-B-001", "orden_compra_id": guia_b["orden_compra_id"]},
    )
    assert informe_b_resp.status_code == 201, informe_b_resp.text
    informe_b = informe_b_resp.json()
    assert informe_b["monto_conforme_total"] == pytest.approx(15 * 5.5)
    assert informe_b["monto_retenido_total"] == pytest.approx(5 * 5.5)
    assert informe_b["monto_penalidad_total"] == pytest.approx(5 * 5.5)
    detalle_b = informe_b["detalle"][0]
    assert detalle_b["cantidad_conforme"] == pytest.approx(15.0)
    assert detalle_b["cantidad_retenida"] == pytest.approx(5.0)
