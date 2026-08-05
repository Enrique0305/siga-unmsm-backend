"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Módulo 01 Planificación anual: ración anual (crear -> detalle -> cambiar
estado) -> menú quincenal (crear -> agregar día -> cambiar estado por toda
la cadena) -> platos (RN-22: solo receta VIGENTE) -> catálogos de
sede/centro de consumo. Antes de esta sesión no había testing dedicado a
este módulo (los demás test_*.py solo lo usaban como fixture).
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
                codigo="ALM-TEST",
                nombre="Almacén Test",
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


@pytest.mark.asyncio
async def test_racion_anual_crear_detalle_estado(client: AsyncClient):
    headers = _headers_admin()

    crear = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2026, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    assert crear.status_code == 201, crear.text
    racion = crear.json()
    assert racion["estado"] == "BORRADOR"
    racion_id = racion["racion_anual_id"]

    detalle = await client.get(f"/api/v1/planificacion/raciones-anuales/{racion_id}", headers=headers)
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["anio"] == 2026

    no_encontrado = await client.get("/api/v1/planificacion/raciones-anuales/999999", headers=headers)
    assert no_encontrado.status_code == 404

    aprobar = await client.patch(
        f"/api/v1/planificacion/raciones-anuales/{racion_id}/estado", headers=headers, json={"estado": "APROBADO"}
    )
    assert aprobar.status_code == 200, aprobar.text
    assert aprobar.json()["estado"] == "APROBADO"

    # APROBADO es terminal
    invalida = await client.patch(
        f"/api/v1/planificacion/raciones-anuales/{racion_id}/estado", headers=headers, json={"estado": "BORRADOR"}
    )
    assert invalida.status_code == 422


@pytest.mark.asyncio
async def test_menu_quincenal_dias_platos_rn22_y_estado(client: AsyncClient):
    headers = _headers_admin()

    racion_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2026, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    racion_id = racion_resp.json()["racion_anual_id"]

    menu_resp = await client.post(
        "/api/v1/planificacion/menus-quincenales",
        headers=headers,
        json={"racion_anual_id": racion_id, "quincena_inicio": "2026-08-01", "quincena_fin": "2026-08-15"},
    )
    assert menu_resp.status_code == 201, menu_resp.text
    menu = menu_resp.json()
    assert menu["estado"] == "BORRADOR"
    assert menu["aprobado_por_id"] is None
    menu_id = menu["menu_id"]

    listado = await client.get("/api/v1/planificacion/menus-quincenales", headers=headers)
    assert listado.status_code == 200, listado.text
    assert listado.json()["total"] == 1

    filtrado = await client.get(
        "/api/v1/planificacion/menus-quincenales", headers=headers, params={"racion_anual_id": racion_id}
    )
    assert filtrado.json()["total"] == 1

    detalle_vacio = await client.get(f"/api/v1/planificacion/menus-quincenales/{menu_id}", headers=headers)
    assert detalle_vacio.status_code == 200, detalle_vacio.text
    assert detalle_vacio.json()["dias"] == []

    dia_resp = await client.post(
        f"/api/v1/planificacion/menus-quincenales/{menu_id}/dias",
        headers=headers,
        json={"fecha": "2026-08-03", "tipo_servicio": "ALMUERZO", "raciones_programadas": 100},
    )
    assert dia_resp.status_code == 201, dia_resp.text
    menu_dia_id = dia_resp.json()["menu_dia_id"]

    detalle_con_dia = await client.get(f"/api/v1/planificacion/menus-quincenales/{menu_id}", headers=headers)
    assert len(detalle_con_dia.json()["dias"]) == 1

    # receta en BORRADOR: RN-22 debe bloquear el plato
    alimento_resp = await client.post(
        "/api/v1/alimentos",
        headers=headers,
        json={
            "codigo": "A001",
            "nombre": "Arroz superior",
            "categoria_alimento_id": 1,
            "tipo": "BASE_TABLA",
            "fuente": "Test",
            "valores": {"energia_kcal": 350},
        },
    )
    assert alimento_resp.status_code == 201, alimento_resp.text
    alimento_id = alimento_resp.json()["alimento_id"]

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
            "ingredientes": [{"alimento_id": alimento_id, "cantidad_bruta_g": 18, "cantidad_neta_g": 17, "unidad_id": 1}],
        },
    )
    assert receta_resp.status_code == 201, receta_resp.text
    receta_id = receta_resp.json()["receta_id"]

    bloqueado = await client.post(
        f"/api/v1/planificacion/dias/{menu_dia_id}/platos", headers=headers, json={"receta_id": receta_id}
    )
    assert bloqueado.status_code == 422
    assert "RN-22" in bloqueado.json()["detail"]

    for estado in ("EN_REVISION", "APROBADO", "VIGENTE"):
        r = await client.patch(f"/api/v1/recetas/{receta_id}/estado", headers=headers, json={"estado": estado})
        assert r.status_code == 200, r.text

    plato_resp = await client.post(
        f"/api/v1/planificacion/dias/{menu_dia_id}/platos", headers=headers, json={"receta_id": receta_id}
    )
    assert plato_resp.status_code == 201, plato_resp.text
    assert plato_resp.json()["receta_nombre"] == "Arroz con pollo"

    dia_detalle = await client.get(f"/api/v1/planificacion/dias/{menu_dia_id}", headers=headers)
    assert len(dia_detalle.json()["platos"]) == 1

    # cadena completa de estados del menú quincenal
    for estado in ("EN_REVISION", "APROBADO", "VIGENTE", "HISTORICO"):
        r = await client.patch(
            f"/api/v1/planificacion/menus-quincenales/{menu_id}/estado", headers=headers, json={"estado": estado}
        )
        assert r.status_code == 200, r.text
        if estado == "APROBADO":
            assert r.json()["aprobado_por_id"] == 1

    # HISTORICO es terminal
    invalida = await client.patch(
        f"/api/v1/planificacion/menus-quincenales/{menu_id}/estado", headers=headers, json={"estado": "BORRADOR"}
    )
    assert invalida.status_code == 422

    no_encontrado = await client.get("/api/v1/planificacion/menus-quincenales/999999", headers=headers)
    assert no_encontrado.status_code == 404


@pytest.mark.asyncio
async def test_catalogos_sedes_y_centros_consumo(client: AsyncClient):
    headers = _headers_admin()

    sedes = await client.get("/api/v1/catalogos/sedes", headers=headers)
    assert sedes.status_code == 200, sedes.text
    assert any(s["nombre"] == "Sede Test" for s in sedes.json())

    centros = await client.get("/api/v1/catalogos/centros-consumo", headers=headers)
    assert centros.status_code == 200, centros.text
    assert any(c["nombre"] == "Comedor Test" for c in centros.json())

    filtrado = await client.get("/api/v1/catalogos/centros-consumo", headers=headers, params={"sede_id": 1})
    assert len(filtrado.json()) == 1

    vacio = await client.get("/api/v1/catalogos/centros-consumo", headers=headers, params={"sede_id": 999})
    assert vacio.json() == []


async def _crear_receta_vigente(client: AsyncClient, headers: dict, codigo: str) -> tuple[int, int]:
    """Alimento + receta VIGENTE con un ingrediente (18g brutos / 17g netos, sin merma,
    numero_raciones_base=100 -> factor_escala=1 con raciones_programadas=100)."""
    alimento_resp = await client.post(
        "/api/v1/alimentos",
        headers=headers,
        json={
            "codigo": f"A-{codigo}",
            "nombre": f"Alimento {codigo}",
            "categoria_alimento_id": 1,
            "tipo": "BASE_TABLA",
            "fuente": "Test",
            "valores": {"energia_kcal": 350},
        },
    )
    assert alimento_resp.status_code == 201, alimento_resp.text
    alimento_id = alimento_resp.json()["alimento_id"]

    receta_resp = await client.post(
        "/api/v1/recetas",
        headers=headers,
        json={
            "codigo": f"REC-{codigo}",
            "nombre": f"Receta {codigo}",
            "categoria_preparacion": "SEGUNDO",
            "numero_raciones_base": 100,
            "tamano_porcion_g": 250,
            "rendimiento_pct": 90,
            "ingredientes": [{"alimento_id": alimento_id, "cantidad_bruta_g": 18, "cantidad_neta_g": 17, "unidad_id": 1}],
        },
    )
    assert receta_resp.status_code == 201, receta_resp.text
    receta_id = receta_resp.json()["receta_id"]

    for estado in ("EN_REVISION", "APROBADO", "VIGENTE"):
        r = await client.patch(f"/api/v1/recetas/{receta_id}/estado", headers=headers, json={"estado": estado})
        assert r.status_code == 200, r.text

    return alimento_id, receta_id


async def _crear_racion_con_dosificacion(
    client: AsyncClient, headers: dict, anio: int, receta_id: int, quincena_inicio: str, fecha_dia: str
) -> int:
    """Ración anual -> menú quincenal -> día -> plato -> dosificación calculada.
    Devuelve el racion_anual_id."""
    racion_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": anio, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    assert racion_resp.status_code == 201, racion_resp.text
    racion_anual_id = racion_resp.json()["racion_anual_id"]

    menu_resp = await client.post(
        "/api/v1/planificacion/menus-quincenales",
        headers=headers,
        json={
            "racion_anual_id": racion_anual_id,
            "quincena_inicio": quincena_inicio,
            "quincena_fin": fecha_dia,
        },
    )
    assert menu_resp.status_code == 201, menu_resp.text
    menu_id = menu_resp.json()["menu_id"]

    dia_resp = await client.post(
        f"/api/v1/planificacion/menus-quincenales/{menu_id}/dias",
        headers=headers,
        json={"fecha": fecha_dia, "tipo_servicio": "ALMUERZO", "raciones_programadas": 100},
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
    assert dosificacion_resp.json()[0]["cantidad_bruta_requerida"] == pytest.approx(18.0)

    return racion_anual_id


@pytest.mark.asyncio
async def test_consolidar_requerimiento_desde_bom(client: AsyncClient):
    headers = _headers_admin()

    alimento_id, receta_id = await _crear_receta_vigente(client, headers, "BOM")

    # el producto (catálogo logístico) debe apuntar al mismo alimento (catálogo
    # nutricional) para que el puente Producto.alimento_id de la consolidación
    # lo encuentre — ver crud/bom_consolidado.py.
    producto_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "codigo": "P-BOM",
            "nombre": "Producto BOM",
            "categoria": "Abarrotes",
            "unidad_id": 1,
            "alimento_id": alimento_id,
        },
    )
    assert producto_resp.status_code == 201, producto_resp.text

    # racion_3: sin dosificación -> 422 al consolidar
    racion_vacia_resp = await client.post(
        "/api/v1/planificacion/raciones-anuales",
        headers=headers,
        json={"sede_id": 1, "centro_consumo_id": 1, "anio": 2030, "poblacion_atendida": 100, "raciones_dia": 100},
    )
    racion_vacia_id = racion_vacia_resp.json()["racion_anual_id"]
    sin_dosificacion = await client.post(
        f"/api/v1/planificacion/raciones-anuales/{racion_vacia_id}/consolidar-requerimiento", headers=headers
    )
    assert sin_dosificacion.status_code == 422
    assert "dosificación" in sin_dosificacion.json()["detail"]

    # racion_1: dosificación real -> consolidar -> ALERTA_CONTRATO (sin contrato todavía)
    racion_1_id = await _crear_racion_con_dosificacion(
        client, headers, 2028, receta_id, "2028-01-01", "2028-01-05"
    )

    consolidar_1 = await client.post(
        f"/api/v1/planificacion/raciones-anuales/{racion_1_id}/consolidar-requerimiento", headers=headers
    )
    assert consolidar_1.status_code == 201, consolidar_1.text
    requerimiento_1 = consolidar_1.json()
    assert requerimiento_1["estado"] == "BORRADOR"
    assert len(requerimiento_1["detalle"]) == 1
    assert requerimiento_1["detalle"][0]["producto_codigo"] == "P-BOM"
    assert requerimiento_1["detalle"][0]["cantidad_estimada_anual"] == pytest.approx(18.0)
    requerimiento_1_id = requerimiento_1["requerimiento_anual_id"]

    bom_1 = await client.get(
        f"/api/v1/planificacion/raciones-anuales/{racion_1_id}/bom-consolidado", headers=headers
    )
    assert bom_1.status_code == 200, bom_1.text
    fila_bom_1 = bom_1.json()[0]
    assert fila_bom_1["cantidad_requerida_total"] == pytest.approx(18.0)
    assert fila_bom_1["saldo_contractual_referencia"] is None
    assert fila_bom_1["estado_suficiencia"] == "ALERTA_CONTRATO"

    # repetir la consolidación sobre la misma ración -> 422 (ya existe un requerimiento)
    repetir = await client.post(
        f"/api/v1/planificacion/raciones-anuales/{racion_1_id}/consolidar-requerimiento", headers=headers
    )
    assert repetir.status_code == 422
    assert "Ya existe" in repetir.json()["detail"]

    # aprueba el requerimiento generado y crea un contrato con saldo suficiente
    for estado in ("EN_REVISION", "APROBADO"):
        r = await client.patch(
            f"/api/v1/requerimientos-anuales/{requerimiento_1_id}/estado", headers=headers, json={"estado": estado}
        )
        assert r.status_code == 200, r.text

    proveedor_resp = await client.post(
        "/api/v1/proveedores", headers=headers, json={"ruc": "20999999999", "razon_social": "Proveedor BOM SAC"}
    )
    assert proveedor_resp.status_code == 201, proveedor_resp.text
    proveedor_id = proveedor_resp.json()["proveedor_id"]

    contrato_resp = await client.post(
        "/api/v1/contratos",
        headers=headers,
        json={
            "numero_contrato": "CTR-BOM-001",
            "proveedor_id": proveedor_id,
            "requerimiento_anual_id": requerimiento_1_id,
            "fecha_inicio": date.today().isoformat(),
            "fecha_fin": (date.today() + timedelta(days=180)).isoformat(),
            "presupuesto_total": 10000,
        },
    )
    assert contrato_resp.status_code == 201, contrato_resp.text
    contrato_id = contrato_resp.json()["contrato_id"]

    producto_id = requerimiento_1["detalle"][0]["producto_id"]
    pc_resp = await client.post(
        f"/api/v1/contratos/{contrato_id}/productos",
        headers=headers,
        json={"producto_id": producto_id, "precio_unitario": 5.0, "cantidad_contratada": 1000},
    )
    assert pc_resp.status_code == 201, pc_resp.text

    # racion_2: mismo producto/almacén, nueva dosificación -> consolidar -> ahora SUFICIENTE
    racion_2_id = await _crear_racion_con_dosificacion(
        client, headers, 2029, receta_id, "2029-01-01", "2029-01-05"
    )
    consolidar_2 = await client.post(
        f"/api/v1/planificacion/raciones-anuales/{racion_2_id}/consolidar-requerimiento", headers=headers
    )
    assert consolidar_2.status_code == 201, consolidar_2.text

    bom_2 = await client.get(
        f"/api/v1/planificacion/raciones-anuales/{racion_2_id}/bom-consolidado", headers=headers
    )
    assert bom_2.status_code == 200, bom_2.text
    fila_bom_2 = bom_2.json()[0]
    assert fila_bom_2["saldo_contractual_referencia"] == pytest.approx(1000.0)
    assert fila_bom_2["estado_suficiencia"] == "SUFICIENTE"
