"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo del módulo Almacén: ingreso desde una línea de inspección
CONFORME (RN-04, valoriza con el precio del contrato, escribe kardex y bin
card) -> RN-20 bloquea a un ALMACENERO sin acceso al almacén -> merma
(decrementa) -> devolución DESDE_COCINA (incrementa) -> ajuste que dejaría
stock negativo (bloqueado) -> transferencia entre almacenes con diferencia
(RN-18: salida inmediata, ingreso solo al confirmar recepción, preserva el
costo original) -> inventario físico con cierre que genera un ajuste
automático.
"""
from datetime import date

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from tests.test_compras import _headers_admin, _preparar_contrato_con_producto, client  # noqa: F401
from tests.test_inspeccion import _crear_guia_completa  # noqa: F401


def _headers_almacenero(almacenes: list[int]) -> dict:
    token = create_access_token(usuario_id=2, rol="ALMACENERO", almacenes=almacenes, acceso_todos_almacenes=False)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_flujo_almacen_completo(client: AsyncClient):
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    guia_ctx = await _crear_guia_completa(client, headers, ctx, "OC-ALM-001", "GR-ALM-001", cantidad=40)

    # 1) inspección totalmente conforme
    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"guia_remision_detalle_id": guia_ctx["guia_remision_detalle_id"], "cantidad_conforme": 40, "cantidad_observada": 0}
            ],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    inspeccion_detalle_id = inspeccion_resp.json()["detalle"][0]["inspeccion_detalle_id"]

    # 2) ubicación interna del almacén 1
    ubicacion_resp = await client.post(
        "/api/v1/ubicaciones", headers=headers, json={"almacen_id": 1, "zona": "A", "estante": "1"}
    )
    assert ubicacion_resp.status_code == 201, ubicacion_resp.text
    ubicacion_id = ubicacion_resp.json()["ubicacion_id"]

    # 3) ingreso a almacén (RN-04): convierte lo conforme en stock real
    ingreso_resp = await client.post(
        "/api/v1/ingresos-almacen",
        headers=headers,
        json={
            "numero_ingreso": "ING-0001",
            "guia_remision_id": guia_ctx["guia_remision_id"],
            "detalle": [
                {"inspeccion_detalle_id": inspeccion_detalle_id, "cantidad_ingresada": 40, "ubicacion_id": ubicacion_id}
            ],
        },
    )
    assert ingreso_resp.status_code == 201, ingreso_resp.text
    ingreso = ingreso_resp.json()
    assert ingreso["detalle"][0]["costo_unitario"] == pytest.approx(5.5)
    producto_id = ctx["producto_id"]

    stock_resp = await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    stock = stock_resp.json()["items"][0]
    assert stock["stock_fisico"] == pytest.approx(40.0)
    assert stock["stock_disponible"] == pytest.approx(40.0)
    assert stock["valor_promedio_unitario"] == pytest.approx(5.5)

    kardex_resp = await client.get("/api/v1/kardex", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    assert kardex_resp.json()["items"][0]["tipo_movimiento"] == "INGRESO"

    # 4) RN-20: un almacenero sin acceso al almacén 1 no puede operar sobre él
    headers_almacenero_sin_acceso = _headers_almacenero(almacenes=[2])
    merma_bloqueada = await client.post(
        "/api/v1/mermas",
        headers=headers_almacenero_sin_acceso,
        json={"almacen_id": 1, "producto_id": producto_id, "cantidad": 5, "motivo": "Rotura"},
    )
    assert merma_bloqueada.status_code == 403

    # 5) merma (decrementa)
    merma_resp = await client.post(
        "/api/v1/mermas", headers=headers, json={"almacen_id": 1, "producto_id": producto_id, "cantidad": 5, "motivo": "Rotura"}
    )
    assert merma_resp.status_code == 201, merma_resp.text

    # 6) devolución DESDE_COCINA (incrementa)
    devolucion_resp = await client.post(
        "/api/v1/devoluciones",
        headers=headers,
        json={"almacen_id": 1, "producto_id": producto_id, "tipo": "DESDE_COCINA", "cantidad": 3},
    )
    assert devolucion_resp.status_code == 201, devolucion_resp.text

    stock_tras_movs = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_tras_movs["stock_fisico"] == pytest.approx(38.0)  # 40 - 5 + 3

    # 7) ajuste que dejaría stock físico negativo -> bloqueado
    ajuste_bloqueado = await client.post(
        "/api/v1/ajustes-inventario",
        headers=headers,
        json={"almacen_id": 1, "producto_id": producto_id, "cantidad_ajuste": -1000, "motivo": "prueba de límite"},
    )
    assert ajuste_bloqueado.status_code == 422

    # 8) transferencia almacén 1 -> almacén 2, con diferencia en la recepción
    transferencia_resp = await client.post(
        "/api/v1/transferencias",
        headers=headers,
        json={
            "numero_transferencia": "TR-0001",
            "almacen_origen_id": 1,
            "almacen_destino_id": 2,
            "detalle": [{"producto_id": producto_id, "cantidad_enviada": 10}],
        },
    )
    assert transferencia_resp.status_code == 201, transferencia_resp.text
    transferencia = transferencia_resp.json()
    assert transferencia["estado"] == "EN_TRANSITO"
    transferencia_id = transferencia["transferencia_id"]
    transferencia_detalle_id = transferencia["detalle"][0]["transferencia_detalle_id"]

    stock_origen_tras_salida = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_origen_tras_salida["stock_fisico"] == pytest.approx(28.0)  # 38 - 10

    recepcion_resp = await client.post(
        f"/api/v1/transferencias/{transferencia_id}/recepcion",
        headers=headers,
        json={"detalle": [{"transferencia_detalle_id": transferencia_detalle_id, "cantidad_recibida": 8, "observacion_diferencia": "Merma en tránsito"}]},
    )
    assert recepcion_resp.status_code == 200, recepcion_resp.text
    assert recepcion_resp.json()["estado"] == "RECIBIDA_CON_DIFERENCIA"

    stock_destino = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 2, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_destino["stock_fisico"] == pytest.approx(8.0)
    assert stock_destino["valor_promedio_unitario"] == pytest.approx(5.5)  # preserva el costo de la salida

    # 9) inventario físico en almacén 1: conteo con diferencia y cierre
    inventario_resp = await client.post(
        "/api/v1/inventarios-fisicos",
        headers=headers,
        json={
            "almacen_id": 1,
            "fecha_conteo": date.today().isoformat(),
            "detalle": [{"producto_id": producto_id, "stock_contado": 30}],  # sistema=28, contado=30 -> +2
        },
    )
    assert inventario_resp.status_code == 201, inventario_resp.text
    inventario = inventario_resp.json()
    assert inventario["detalle"][0]["stock_sistema"] == pytest.approx(28.0)
    assert inventario["detalle"][0]["diferencia"] == pytest.approx(2.0)
    inventario_id = inventario["inventario_fisico_id"]

    cierre_resp = await client.post(f"/api/v1/inventarios-fisicos/{inventario_id}/cerrar", headers=headers)
    assert cierre_resp.status_code == 200, cierre_resp.text
    cierre = cierre_resp.json()
    assert cierre["estado"] == "CERRADO"
    assert cierre["detalle"][0]["ajuste_generado_id"] is not None

    stock_tras_cierre = (
        await client.get("/api/v1/stock-almacen", headers=headers, params={"almacen_id": 1, "producto_id": producto_id})
    ).json()["items"][0]
    assert stock_tras_cierre["stock_fisico"] == pytest.approx(30.0)

    # 10) no se puede cerrar dos veces
    cierre_dup = await client.post(f"/api/v1/inventarios-fisicos/{inventario_id}/cerrar", headers=headers)
    assert cierre_dup.status_code == 422
