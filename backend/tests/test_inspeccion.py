"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo de Inspección/Actas: inspección con línea dividida
conforme/observada (deriva `resultado` y avanza guia_remision.estado
PENDIENTE->OBSERVADO) -> acta de observación -> subsanación -> re-inspección
(CONFORME cierra el acta como SUBSANADA y la guía pasa a SUBSANADO; NO_CONFORME
la deja RECHAZADA, también concluyendo el proceso de subsanación de la guía).
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.test_compras import _headers_admin, _headers_rol, _preparar_contrato_con_producto, client  # noqa: F401


async def _crear_guia_completa(
    client: AsyncClient,
    headers: dict,
    ctx: dict,
    numero_oc: str,
    numero_guia: str,
    cantidad: float = 40,
    semana_offset_dias: int = 0,
    fecha_vencimiento: date | None = None,
) -> dict:
    """Emite una OC en un solo almacén, su pedido semanal, y una guía con
    entrega completa. Devuelve ids útiles para inspeccionar. `cantidad`
    debe caber dentro del saldo del producto contratado (100 en total,
    ver _preparar_contrato_con_producto); `semana_offset_dias` evita
    chocar con RN-16 (único por menú+almacén+semana_inicio) cuando se
    llama más de una vez en el mismo test."""
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
                    "cantidad_solicitada": cantidad,
                    "distribucion": [{"almacen_id": 1, "cantidad_distribuida": cantidad}],
                }
            ],
        },
    )
    assert oc_resp.status_code == 201, oc_resp.text
    oc = oc_resp.json()
    orden_compra_id = oc["orden_compra_id"]
    orden_compra_detalle_id = oc["detalle"][0]["orden_compra_detalle_id"]

    semana_inicio = date.today() + timedelta(days=semana_offset_dias)
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

    detalle_guia = {"orden_compra_detalle_id": orden_compra_detalle_id, "cantidad_entregada": cantidad}
    if fecha_vencimiento is not None:
        detalle_guia["fecha_vencimiento"] = fecha_vencimiento.isoformat()

    guia_resp = await client.post(
        "/api/v1/guias-remision",
        headers=headers,
        json={
            "numero_guia": numero_guia,
            "proveedor_id": ctx["proveedor_id"],
            "orden_compra_id": orden_compra_id,
            "pedido_semanal_id": pedido_resp.json()["pedido_semanal_id"],
            "almacen_destino_id": 1,
            "fecha_entrega": date.today().isoformat(),
            "detalle": [detalle_guia],
        },
    )
    assert guia_resp.status_code == 201, guia_resp.text
    guia = guia_resp.json()
    return {
        "guia_remision_id": guia["guia_remision_id"],
        "guia_remision_detalle_id": guia["detalle"][0]["guia_remision_detalle_id"],
        "orden_compra_id": orden_compra_id,
        "orden_compra_detalle_id": orden_compra_detalle_id,
    }


@pytest.mark.asyncio
async def test_flujo_inspeccion_completo(client: AsyncClient):
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    guia_ctx = await _crear_guia_completa(client, headers, ctx, "OC-INSP-001", "GR-INSP-001")

    # 1) la suma conforme+observada no cuadra con lo entregado (40) -> bloqueada
    inspeccion_mal = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"], "cantidad_conforme": 10, "cantidad_observada": 10}
            ],
        },
    )
    assert inspeccion_mal.status_code == 422

    # 2) inspección válida: 30 conforme + 10 observada = 40 entregado
    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"], "cantidad_conforme": 30, "cantidad_observada": 10}
            ],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    inspeccion = inspeccion_resp.json()
    detalle_inspeccion = inspeccion["detalle"][0]
    assert detalle_inspeccion["resultado"] == "OBSERVADO"
    inspeccion_detalle_id = detalle_inspeccion["inspeccion_detalle_id"]

    guia_tras_inspeccion = await client.get(f"/api/v1/guias-remision/{guia_ctx['guia_remision_id']}", headers=headers)
    assert guia_tras_inspeccion.json()["estado"] == "OBSERVADO"

    # 3) la misma línea no puede inspeccionarse dos veces
    inspeccion_dup = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"], "cantidad_conforme": 40, "cantidad_observada": 0}
            ],
        },
    )
    assert inspeccion_dup.status_code == 422

    # 4) acta de observación sobre la línea observada
    acta_resp = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id}",
        headers=headers,
        json={"numero_acta": "ACTA-0001", "motivo": "Merma en tránsito", "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat()},
    )
    assert acta_resp.status_code == 201, acta_resp.text
    acta = acta_resp.json()
    assert acta["estado"] == "ABIERTA"
    assert acta["cantidad_observada"] == pytest.approx(10.0)
    assert acta["plazo_vencido"] is False
    acta_id = acta["acta_observacion_id"]

    # 5) no se puede levantar una segunda acta sobre la misma línea
    acta_dup = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id}",
        headers=headers,
        json={"numero_acta": "ACTA-0002", "motivo": "Duplicado", "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat()},
    )
    assert acta_dup.status_code == 422

    # 6) subsanación (evidencia del proveedor) + re-inspección CONFORME
    subsanacion_resp = await client.post(
        f"/api/v1/actas-observacion/{acta_id}/subsanaciones",
        headers=headers,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "Reposición del faltante"},
    )
    assert subsanacion_resp.status_code == 201, subsanacion_resp.text
    subsanacion_id = subsanacion_resp.json()["subsanacion_id"]

    reinspeccion_resp = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_id}/reinspeccion",
        headers=headers,
        json={"resultado_reinspeccion": "CONFORME"},
    )
    assert reinspeccion_resp.status_code == 200, reinspeccion_resp.text
    assert reinspeccion_resp.json()["resultado_reinspeccion"] == "CONFORME"

    acta_final = await client.get(f"/api/v1/actas-observacion/{acta_id}", headers=headers)
    assert acta_final.json()["estado"] == "SUBSANADA"

    guia_final = await client.get(f"/api/v1/guias-remision/{guia_ctx['guia_remision_id']}", headers=headers)
    assert guia_final.json()["estado"] == "SUBSANADO"

    # 7) no se puede volver a registrar un resultado sobre la misma subsanación
    reinspeccion_dup = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_id}/reinspeccion",
        headers=headers,
        json={"resultado_reinspeccion": "CONFORME"},
    )
    assert reinspeccion_dup.status_code == 422

    # 8) camino negativo: NO_CONFORME deja el acta RECHAZADA (terminal) y la
    # guía igual concluye en SUBSANADO (el proceso terminó; Módulo 5 decide
    # CERRADO/PENALIZADO leyendo el estado de cada acta)
    guia_ctx_2 = await _crear_guia_completa(
        client, headers, ctx, "OC-INSP-002", "GR-INSP-002", cantidad=40, semana_offset_dias=7
    )
    inspeccion_2 = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx_2["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx_2["guia_remision_detalle_id"], "cantidad_conforme": 0, "cantidad_observada": 40}
            ],
        },
    )
    assert inspeccion_2.status_code == 201, inspeccion_2.text
    inspeccion_detalle_id_2 = inspeccion_2.json()["detalle"][0]["inspeccion_detalle_id"]

    acta_2 = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id_2}",
        headers=headers,
        json={"numero_acta": "ACTA-0003", "motivo": "Lote vencido", "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat()},
    )
    assert acta_2.status_code == 201, acta_2.text
    acta_id_2 = acta_2.json()["acta_observacion_id"]

    subsanacion_2 = await client.post(
        f"/api/v1/actas-observacion/{acta_id_2}/subsanaciones",
        headers=headers,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "Cambio de lote"},
    )
    subsanacion_id_2 = subsanacion_2.json()["subsanacion_id"]

    reinspeccion_2 = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_id_2}/reinspeccion",
        headers=headers,
        json={"resultado_reinspeccion": "NO_CONFORME"},
    )
    assert reinspeccion_2.status_code == 200, reinspeccion_2.text

    acta_2_final = await client.get(f"/api/v1/actas-observacion/{acta_id_2}", headers=headers)
    assert acta_2_final.json()["estado"] == "RECHAZADA"

    guia_2_final = await client.get(f"/api/v1/guias-remision/{guia_ctx_2['guia_remision_id']}", headers=headers)
    assert guia_2_final.json()["estado"] == "SUBSANADO"


@pytest.mark.asyncio
async def test_rn20_alcance_por_almacen(client: AsyncClient):
    """RN-20: inspecciones.py y actas_observacion.py ahora derivan el
    almacén destino de la guía (vía guia_remision_detalle -> guia_remision)
    y validan el acceso del usuario antes de escribir."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    guia_ctx = await _crear_guia_completa(client, headers, ctx, "OC-INSP-RN20", "GR-INSP-RN20", cantidad=40)

    headers_inspector_sin_acceso = _headers_rol("INSPECTOR", almacenes=[2])
    headers_inspector_con_acceso = _headers_rol("INSPECTOR", almacenes=[1])

    # 1) crear inspección sin acceso al almacén destino de la guía (1) -> 403
    inspeccion_bloqueada = await client.post(
        "/api/v1/inspecciones",
        headers=headers_inspector_sin_acceso,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {
                    "guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"],
                    "cantidad_conforme": 30,
                    "cantidad_observada": 10,
                }
            ],
        },
    )
    assert inspeccion_bloqueada.status_code == 403
    assert "RN-20" in inspeccion_bloqueada.json()["detail"]

    inspeccion_ok = await client.post(
        "/api/v1/inspecciones",
        headers=headers_inspector_con_acceso,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {
                    "guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"],
                    "cantidad_conforme": 30,
                    "cantidad_observada": 10,
                }
            ],
        },
    )
    assert inspeccion_ok.status_code == 201, inspeccion_ok.text
    inspeccion_detalle_id = inspeccion_ok.json()["detalle"][0]["inspeccion_detalle_id"]

    # 2) crear acta sin acceso -> 403
    acta_bloqueada = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id}",
        headers=headers_inspector_sin_acceso,
        json={
            "numero_acta": "ACTA-RN20-1",
            "motivo": "test",
            "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert acta_bloqueada.status_code == 403

    acta_resp = await client.post(
        f"/api/v1/actas-observacion/desde-inspeccion-detalle/{inspeccion_detalle_id}",
        headers=headers_inspector_con_acceso,
        json={
            "numero_acta": "ACTA-RN20-1",
            "motivo": "test",
            "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert acta_resp.status_code == 201, acta_resp.text
    acta_id = acta_resp.json()["acta_observacion_id"]

    # 3) subsanación (rol PROVEEDOR) sin acceso -> 403
    # proveedor_id igual en ambos tokens: aísla el chequeo a la dimensión
    # de almacén (RN-20), el de proveedor (Sesión 12) se prueba aparte.
    headers_proveedor_sin_acceso = _headers_rol("PROVEEDOR", almacenes=[2], proveedor_id=ctx["proveedor_id"])
    headers_proveedor_con_acceso = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=ctx["proveedor_id"])

    subsanacion_bloqueada = await client.post(
        f"/api/v1/actas-observacion/{acta_id}/subsanaciones",
        headers=headers_proveedor_sin_acceso,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "test"},
    )
    assert subsanacion_bloqueada.status_code == 403

    subsanacion_resp = await client.post(
        f"/api/v1/actas-observacion/{acta_id}/subsanaciones",
        headers=headers_proveedor_con_acceso,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "test"},
    )
    assert subsanacion_resp.status_code == 201, subsanacion_resp.text
    subsanacion_id = subsanacion_resp.json()["subsanacion_id"]

    # 4) reinspección sin acceso -> 403
    reinspeccion_bloqueada = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_id}/reinspeccion",
        headers=headers_inspector_sin_acceso,
        json={"resultado_reinspeccion": "CONFORME"},
    )
    assert reinspeccion_bloqueada.status_code == 403

    reinspeccion_ok = await client.patch(
        f"/api/v1/actas-observacion/subsanaciones/{subsanacion_id}/reinspeccion",
        headers=headers_inspector_con_acceso,
        json={"resultado_reinspeccion": "CONFORME"},
    )
    assert reinspeccion_ok.status_code == 200, reinspeccion_ok.text


@pytest.mark.asyncio
async def test_rn_alcance_proveedor_subsanacion(client: AsyncClient):
    """Sesión 12: solo el proveedor dueño de la guía observada puede
    presentar una subsanación sobre su propia acta — otro proveedor
    autenticado no puede, aunque conozca el id del acta."""
    headers = _headers_admin()
    ctx_a = await _preparar_contrato_con_producto(
        client,
        headers,
        producto_codigo="P-PROV-INSP-A",
        proveedor_ruc="20111111111",
        proveedor_razon_social="Proveedor Inspección A",
        numero_contrato="CTR-PROV-INSP-A",
    )
    guia_ctx = await _crear_guia_completa(client, headers, ctx_a, "OC-PROV-INSP-A", "GR-PROV-INSP-A", cantidad=40)

    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {
                    "guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"],
                    "cantidad_conforme": 30,
                    "cantidad_observada": 10,
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
            "numero_acta": "ACTA-PROV-INSP-1",
            "motivo": "test",
            "plazo_subsanacion": (date.today() + timedelta(days=5)).isoformat(),
        },
    )
    assert acta_resp.status_code == 201, acta_resp.text
    acta_id = acta_resp.json()["acta_observacion_id"]

    proveedor_b_resp = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20222222222", "razon_social": "Proveedor Inspección B"}
    )
    proveedor_b_id = proveedor_b_resp.json()["proveedor_id"]

    headers_proveedor_ajeno = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=proveedor_b_id)
    headers_proveedor_propio = _headers_rol("PROVEEDOR", almacenes=[1], proveedor_id=ctx_a["proveedor_id"])

    subsanacion_bloqueada = await client.post(
        f"/api/v1/actas-observacion/{acta_id}/subsanaciones",
        headers=headers_proveedor_ajeno,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "test"},
    )
    assert subsanacion_bloqueada.status_code == 403

    subsanacion_ok = await client.post(
        f"/api/v1/actas-observacion/{acta_id}/subsanaciones",
        headers=headers_proveedor_propio,
        json={"fecha_presentacion": date.today().isoformat(), "descripcion": "test"},
    )
    assert subsanacion_ok.status_code == 201, subsanacion_ok.text
