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
from tests.test_inspeccion import _crear_guia_completa, _crear_guia_en_almacen  # noqa: F401


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


@pytest.mark.asyncio
async def test_filtro_sede_id_valorizacion_inventario(client: AsyncClient):
    """Deuda técnica: /reportes/valorizacion-inventario gana sede_id
    (Almacen.sede_id) — dos almacenes en sedes distintas, cada uno con
    stock propio, el filtro debe aislar solo el de la sede pedida."""
    from app.models.organizacion import Almacen, Sede

    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)

    async with client.session_factory() as db:
        db.add(Sede(sede_id=2, nombre="Sede Test 2"))
        await db.flush()
        db.add(
            Almacen(
                almacen_id=2,
                codigo="ALM-TEST-2",
                nombre="Almacén Test 2",
                sede_id=2,
                tipo_comedor="ESTUDIANTES",
                responsable_id=1,
            )
        )
        await db.commit()

    guia_sede_1 = await _crear_guia_en_almacen(client, headers, ctx, "OC-SEDE-1", "GR-SEDE-1", almacen_id=1)
    await _ingresar_stock(client, headers, guia_sede_1, cantidad=40)

    guia_sede_2 = await _crear_guia_en_almacen(client, headers, ctx, "OC-SEDE-2", "GR-SEDE-2", almacen_id=2)
    await _ingresar_stock(client, headers, guia_sede_2, cantidad=40)

    resp_sede_1 = await client.get("/api/v1/reportes/valorizacion-inventario", headers=headers, params={"sede_id": 1})
    assert resp_sede_1.status_code == 200, resp_sede_1.text
    filas_1 = resp_sede_1.json()
    assert len(filas_1) == 1
    assert filas_1[0]["almacen_id"] == 1
    assert filas_1[0]["valor_valorizado_total"] == pytest.approx(40 * 5.5)

    resp_sede_2 = await client.get("/api/v1/reportes/valorizacion-inventario", headers=headers, params={"sede_id": 2})
    assert resp_sede_2.status_code == 200, resp_sede_2.text
    filas_2 = resp_sede_2.json()
    assert len(filas_2) == 1
    assert filas_2[0]["almacen_id"] == 2
    assert filas_2[0]["valor_valorizado_total"] == pytest.approx(40 * 5.5)

    resp_sin_filtro = await client.get("/api/v1/reportes/valorizacion-inventario", headers=headers)
    assert len(resp_sin_filtro.json()) == 2


@pytest.mark.asyncio
async def test_filtro_proveedor_id_comparativo_consumo(client: AsyncClient):
    """Deuda técnica: /reportes/comparativo-consumo gana proveedor_id, que
    filtra solo cantidad_comprada (única métrica con dimensión de proveedor
    real) — mismo producto contratado por dos proveedores independientes,
    cada uno con su propia OC."""
    from datetime import timedelta

    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    producto_id = ctx["producto_id"]

    guia_a = await _crear_guia_completa(client, headers, ctx, "OC-PROV-A", "GR-PROV-A", cantidad=20, semana_offset_dias=0)
    await _ingresar_stock(client, headers, guia_a, cantidad=20)

    # segundo proveedor, contratando el mismo producto
    racion_b = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2027, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    assert racion_b.status_code == 201, racion_b.text
    racion_anual_id_b = racion_b.json()["racion_anual_id"]

    req_b = await client.post(
        "/api/v1/requerimientos-anuales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id_b,
            "presupuesto_referencial_total": 5000,
            "detalle": [
                {"producto_id": producto_id, "cantidad_estimada_anual": 1000, "unidad_id": 1, "presupuesto_referencial": 5000}
            ],
        },
    )
    assert req_b.status_code == 201, req_b.text
    requerimiento_anual_id_b = req_b.json()["requerimiento_anual_id"]
    for estado in ("EN_REVISION", "APROBADO"):
        r = await client.patch(
            f"/api/v1/requerimientos-anuales/{requerimiento_anual_id_b}/estado", headers=headers, json={"estado": estado}
        )
        assert r.status_code == 200, r.text

    proveedor_b = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20999999999", "razon_social": "Proveedor B SAC"}
    )
    assert proveedor_b.status_code == 201, proveedor_b.text
    proveedor_id_b = proveedor_b.json()["proveedor_id"]

    contrato_b = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-2026-B",
            "proveedor_id": proveedor_id_b,
            "requerimiento_anual_id": requerimiento_anual_id_b,
            "fecha_inicio": date.today().isoformat(),
            "fecha_fin": (date.today() + timedelta(days=200)).isoformat(),
            "presupuesto_total": 5000,
        },
    )
    assert contrato_b.status_code == 201, contrato_b.text
    contrato_id_b = contrato_b.json()["contrato_id"]

    pc_b = await client.post(
        f"/api/v1/contratos/{contrato_id_b}/productos",
        headers=headers,
        json={"producto_id": producto_id, "precio_unitario": 5.5, "cantidad_contratada": 100},
    )
    assert pc_b.status_code == 201, pc_b.text
    producto_contratado_id_b = pc_b.json()["producto_contratado_id"]

    menu_b = await client.post(
        "/api/v1/planificacion/menus-quincenales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id_b,
            "quincena_inicio": date.today().isoformat(),
            "quincena_fin": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert menu_b.status_code == 201, menu_b.text
    menu_id_b = menu_b.json()["menu_id"]

    ctx_b = {
        "producto_id": producto_id,
        "proveedor_id": proveedor_id_b,
        "contrato_id": contrato_id_b,
        "producto_contratado_id": producto_contratado_id_b,
        "menu_id": menu_id_b,
    }
    guia_b = await _crear_guia_completa(client, headers, ctx_b, "OC-PROV-B", "GR-PROV-B", cantidad=15, semana_offset_dias=14)
    await _ingresar_stock(client, headers, guia_b, cantidad=15)

    fecha_inicio = date.today().replace(day=1)
    fecha_fin = date.today()

    resp_sin_filtro = await client.get(
        "/api/v1/reportes/comparativo-consumo",
        headers=headers,
        params={"producto_id": producto_id, "fecha_inicio": fecha_inicio.isoformat(), "fecha_fin": fecha_fin.isoformat()},
    )
    assert resp_sin_filtro.status_code == 200, resp_sin_filtro.text
    assert resp_sin_filtro.json()["cantidad_comprada"] == pytest.approx(35.0)  # 20 (A) + 15 (B)

    resp_proveedor_a = await client.get(
        "/api/v1/reportes/comparativo-consumo",
        headers=headers,
        params={
            "producto_id": producto_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "proveedor_id": ctx["proveedor_id"],
        },
    )
    assert resp_proveedor_a.status_code == 200, resp_proveedor_a.text
    assert resp_proveedor_a.json()["cantidad_comprada"] == pytest.approx(20.0)

    resp_proveedor_b = await client.get(
        "/api/v1/reportes/comparativo-consumo",
        headers=headers,
        params={
            "producto_id": producto_id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "proveedor_id": proveedor_id_b,
        },
    )
    assert resp_proveedor_b.status_code == 200, resp_proveedor_b.text
    assert resp_proveedor_b.json()["cantidad_comprada"] == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_filtro_producto_id_alertas(client: AsyncClient):
    """Deuda técnica: /reportes/alertas gana producto_id, aplicado por
    igual a los 3 sub-reportes (todos ya unen contra Producto) — dos
    productos con stock bajo en el mismo almacén, el filtro debe aislar
    solo el producto pedido."""
    headers = _headers_admin()
    ctx = await _preparar_contrato_con_producto(client, headers)
    producto_id_a = ctx["producto_id"]

    producto_b_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P002", "nombre": "Aceite vegetal", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert producto_b_resp.status_code == 201, producto_b_resp.text
    producto_id_b = producto_b_resp.json()["producto_id"]

    pc_b = await client.post(
        f"/api/v1/contratos/{ctx['contrato_id']}/productos",
        headers=headers,
        json={"producto_id": producto_id_b, "precio_unitario": 5.5, "cantidad_contratada": 100},
    )
    assert pc_b.status_code == 201, pc_b.text
    producto_contratado_id_b = pc_b.json()["producto_contratado_id"]

    await client.patch(f"/api/v1/productos/{producto_id_a}", headers=headers, json={"stock_minimo_referencial": 30})
    await client.patch(f"/api/v1/productos/{producto_id_b}", headers=headers, json={"stock_minimo_referencial": 30})

    guia_a = await _crear_guia_completa(client, headers, ctx, "OC-PID-A", "GR-PID-A", cantidad=20, semana_offset_dias=0)
    await _ingresar_stock(client, headers, guia_a, cantidad=20)

    ctx_b = {**ctx, "producto_contratado_id": producto_contratado_id_b}
    guia_b = await _crear_guia_completa(client, headers, ctx_b, "OC-PID-B", "GR-PID-B", cantidad=20, semana_offset_dias=7)
    await _ingresar_stock(client, headers, guia_b, cantidad=20)

    resp_sin_filtro = await client.get("/api/v1/reportes/alertas", headers=headers, params={"almacen_id": 1})
    assert resp_sin_filtro.status_code == 200, resp_sin_filtro.text
    assert len(resp_sin_filtro.json()["stock_bajo"]) == 2

    resp_producto_a = await client.get(
        "/api/v1/reportes/alertas", headers=headers, params={"almacen_id": 1, "producto_id": producto_id_a}
    )
    assert resp_producto_a.status_code == 200, resp_producto_a.text
    stock_bajo_a = resp_producto_a.json()["stock_bajo"]
    assert len(stock_bajo_a) == 1
    assert stock_bajo_a[0]["producto_id"] == producto_id_a

    resp_producto_b = await client.get(
        "/api/v1/reportes/alertas", headers=headers, params={"almacen_id": 1, "producto_id": producto_id_b}
    )
    assert resp_producto_b.status_code == 200, resp_producto_b.text
    stock_bajo_b = resp_producto_b.json()["stock_bajo"]
    assert len(stock_bajo_b) == 1
    assert stock_bajo_b[0]["producto_id"] == producto_id_b
