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
from tests.test_inspeccion import _crear_guia_completa, _crear_guia_en_almacen  # noqa: F401


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


async def _ingresar_stock_en_almacen(client: AsyncClient, headers: dict, ctx: dict, numero_oc: str, numero_guia: str, numero_ingreso: str, almacen_id: int) -> None:
    guia = await _crear_guia_en_almacen(client, headers, ctx, numero_oc, numero_guia, almacen_id=almacen_id)
    inspeccion_resp = await client.post(
        "/api/v1/inspecciones",
        headers=headers,
        json={
            "guia_remision_id": guia["guia_remision_id"],
            "detalle": [{"guia_remision_detalle_id": guia["guia_remision_detalle_id"], "cantidad_conforme": 40, "cantidad_observada": 0}],
        },
    )
    assert inspeccion_resp.status_code == 201, inspeccion_resp.text
    inspeccion_detalle_id = inspeccion_resp.json()["detalle"][0]["inspeccion_detalle_id"]

    ingreso_resp = await client.post(
        "/api/v1/ingresos-almacen",
        headers=headers,
        json={
            "numero_ingreso": numero_ingreso,
            "guia_remision_id": guia["guia_remision_id"],
            "detalle": [{"inspeccion_detalle_id": inspeccion_detalle_id, "cantidad_ingresada": 40}],
        },
    )
    assert ingreso_resp.status_code == 201, ingreso_resp.text


@pytest.mark.asyncio
async def test_rn20_lecturas_almacen(client: AsyncClient):
    """Sesión 15: cierra RN-20 en las lecturas (GET) de ubicaciones.py,
    ingresos_almacen.py, stock.py, inventarios_fisicos.py y
    transferencias_almacen.py — hasta la Sesión 11 solo las escrituras
    estaban acotadas por almacén."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    producto_id = ctx["producto_id"]

    ubicacion_1 = await client.post("/api/v1/ubicaciones", headers=headers, json={"almacen_id": 1, "zona": "A", "estante": "1"})
    assert ubicacion_1.status_code == 201, ubicacion_1.text
    ubicacion_2 = await client.post("/api/v1/ubicaciones", headers=headers, json={"almacen_id": 2, "zona": "A", "estante": "1"})
    assert ubicacion_2.status_code == 201, ubicacion_2.text

    await _ingresar_stock_en_almacen(client, headers, ctx, "OC-LEC-ALM-1", "GR-LEC-ALM-1", "ING-LEC-1", almacen_id=1)
    await _ingresar_stock_en_almacen(client, headers, ctx, "OC-LEC-ALM-2", "GR-LEC-ALM-2", "ING-LEC-2", almacen_id=2)

    ingresos_admin = (await client.get("/api/v1/ingresos-almacen", headers=headers)).json()["items"]
    ingreso_1_id = next(i["ingreso_almacen_id"] for i in ingresos_admin if i["numero_ingreso"] == "ING-LEC-1")
    ingreso_2_id = next(i["ingreso_almacen_id"] for i in ingresos_admin if i["numero_ingreso"] == "ING-LEC-2")

    inventario_1 = await client.post(
        "/api/v1/inventarios-fisicos",
        headers=headers,
        json={"almacen_id": 1, "fecha_conteo": date.today().isoformat(), "detalle": [{"producto_id": producto_id, "stock_contado": 40}]},
    )
    assert inventario_1.status_code == 201, inventario_1.text
    inventario_2 = await client.post(
        "/api/v1/inventarios-fisicos",
        headers=headers,
        json={"almacen_id": 2, "fecha_conteo": date.today().isoformat(), "detalle": [{"producto_id": producto_id, "stock_contado": 40}]},
    )
    assert inventario_2.status_code == 201, inventario_2.text

    transferencia_resp = await client.post(
        "/api/v1/transferencias",
        headers=headers,
        json={
            "numero_transferencia": "TR-LEC-001",
            "almacen_origen_id": 1,
            "almacen_destino_id": 2,
            "detalle": [{"producto_id": producto_id, "cantidad_enviada": 5}],
        },
    )
    assert transferencia_resp.status_code == 201, transferencia_resp.text

    headers_restringido = _headers_almacenero(almacenes=[1])

    # ------------------------------------------------------------------ ubicaciones
    lista_ubicaciones = await client.get("/api/v1/ubicaciones", headers=headers_restringido)
    assert lista_ubicaciones.status_code == 200, lista_ubicaciones.text
    assert {u["almacen_id"] for u in lista_ubicaciones.json()["items"]} == {1}

    # --------------------------------------------------------------- ingresos a almacén
    lista_ingresos = await client.get("/api/v1/ingresos-almacen", headers=headers_restringido)
    assert lista_ingresos.status_code == 200, lista_ingresos.text
    assert {i["numero_ingreso"] for i in lista_ingresos.json()["items"]} == {"ING-LEC-1"}

    assert (await client.get(f"/api/v1/ingresos-almacen/{ingreso_1_id}", headers=headers_restringido)).status_code == 200
    assert (await client.get(f"/api/v1/ingresos-almacen/{ingreso_2_id}", headers=headers_restringido)).status_code == 403

    # ------------------------------------------------------------------- stock y kardex
    lista_stock = await client.get("/api/v1/stock-almacen", headers=headers_restringido)
    assert lista_stock.status_code == 200, lista_stock.text
    assert {s["almacen_id"] for s in lista_stock.json()["items"]} == {1}

    lista_kardex = await client.get("/api/v1/kardex", headers=headers_restringido)
    assert lista_kardex.status_code == 200, lista_kardex.text
    assert {k["almacen_id"] for k in lista_kardex.json()["items"]} == {1}

    # -------------------------------------------------------------- inventarios físicos
    lista_inventarios = await client.get("/api/v1/inventarios-fisicos", headers=headers_restringido)
    assert lista_inventarios.status_code == 200, lista_inventarios.text
    assert {i["almacen_id"] for i in lista_inventarios.json()["items"]} == {1}

    assert (
        await client.get(f"/api/v1/inventarios-fisicos/{inventario_1.json()['inventario_fisico_id']}", headers=headers_restringido)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/inventarios-fisicos/{inventario_2.json()['inventario_fisico_id']}", headers=headers_restringido)
    ).status_code == 403

    # ---------------------------------------------------------------------- transferencias
    # política OR: el usuario solo tiene acceso al almacén 1 (origen), pero
    # igual debe poder ver la transferencia hacia el almacén 2.
    lista_transferencias = await client.get("/api/v1/transferencias", headers=headers_restringido)
    assert lista_transferencias.status_code == 200, lista_transferencias.text
    assert len(lista_transferencias.json()["items"]) == 1

    transferencia_id = transferencia_resp.json()["transferencia_id"]
    assert (await client.get(f"/api/v1/transferencias/{transferencia_id}", headers=headers_restringido)).status_code == 200

    # regresión: ADMIN sigue viendo todo
    assert len((await client.get("/api/v1/ingresos-almacen", headers=headers)).json()["items"]) == 2
    assert len((await client.get("/api/v1/inventarios-fisicos", headers=headers)).json()["items"]) == 2
