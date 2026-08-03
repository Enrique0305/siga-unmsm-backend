"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica el flujo real: crear alimento -> crear receta -> cálculo
nutricional automático -> RN-22 (solo VIGENTE en menús) -> RN-25
(versionado en vez de edición).
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.core.security import create_access_token
import app.models  # noqa: F401  registra los modelos


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Semilla mínima: unidad de medida y categoría de alimento (en producción
    # las crea el catálogo base; aquí no hay endpoint de alta para categorías).
    from app.models.catalogos import CategoriaAlimento, UnidadMedida

    async with TestSession() as seed_session:
        seed_session.add(CategoriaAlimento(categoria_alimento_id=1, nombre="Cereales"))
        seed_session.add(UnidadMedida(unidad_id=1, codigo="KG", nombre="Kilogramo"))
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
async def test_flujo_receta_completo(client: AsyncClient):
    headers = _headers_admin()

    # 1) categoría + alimento base con valores nutricionales conocidos
    cat = await client.post(
        "/api/v1/alimentos",
        headers=headers,
        json={
            "codigo": "A001",
            "nombre": "Arroz superior",
            "categoria_alimento_id": 1,
            "tipo": "BASE_TABLA",
            "fuente": "Test",
            "valores": {"energia_kcal": 350, "proteinas_g": 7, "sodio_mg": 5},
        },
    )
    assert cat.status_code == 201, cat.text

    # 2) crear receta con ese alimento como ingrediente
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
            "ingredientes": [
                {
                    "alimento_id": 1,
                    "cantidad_bruta_g": 18,
                    "cantidad_neta_g": 17,
                    "unidad_id": 1,
                    "merma_pct": 4,
                }
            ],
        },
    )
    assert receta_resp.status_code == 201, receta_resp.text
    receta = receta_resp.json()
    assert receta["estado"] == "BORRADOR"
    # cálculo nutricional: 17g de 350kcal/100g = 59.5kcal total / 100 raciones = 0.595kcal/ración
    assert receta["valor_nutricional"]["energia_kcal_total"] == pytest.approx(59.5, rel=0.01)
    assert receta["valor_nutricional"]["energia_kcal_racion"] == pytest.approx(0.595, rel=0.01)

    receta_id = receta["receta_id"]

    # 3) RN-22: no se puede agregar a un menú si no está VIGENTE
    menu_dia_id = 1  # no existe, pero el chequeo de estado ocurre antes de tocarlo
    plato_resp = await client.post(
        f"/api/v1/planificacion/dias/{menu_dia_id}/platos",
        headers=headers,
        json={"receta_id": receta_id},
    )
    assert plato_resp.status_code == 422
    assert "RN-22" in plato_resp.json()["detail"]

    # 4) transición de estado inválida: BORRADOR -> VIGENTE directo debe fallar
    bad = await client.patch(f"/api/v1/recetas/{receta_id}/estado", headers=headers, json={"estado": "VIGENTE"})
    assert bad.status_code == 422

    # 5) transición válida: BORRADOR -> EN_REVISION -> APROBADO -> VIGENTE
    for estado in ("EN_REVISION", "APROBADO", "VIGENTE"):
        r = await client.patch(f"/api/v1/recetas/{receta_id}/estado", headers=headers, json={"estado": estado})
        assert r.status_code == 200, r.text

    # 6) RN-25: crear nueva versión de una receta VIGENTE -> queda en BORRADOR, con nuevo id
    version_resp = await client.post(f"/api/v1/recetas/{receta_id}/versiones", headers=headers)
    assert version_resp.status_code == 201
    nueva = version_resp.json()
    assert nueva["receta_id"] != receta_id
    assert nueva["version"] == 2
    assert nueva["estado"] == "BORRADOR"
    assert nueva["receta_padre_id"] == receta_id
