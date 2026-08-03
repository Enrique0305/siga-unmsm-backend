"""
Test de integración con SQLite en memoria (no requiere MySQL corriendo).
Verifica que el evento global de auditoría (app/core/audit.py) registra
automáticamente cada creación/actualización, sin que ningún crud/*.py haya
tenido que llamarlo explícitamente.
"""
import pytest
from httpx import AsyncClient

from tests.test_compras import _headers_admin, client  # noqa: F401


@pytest.mark.asyncio
async def test_auditoria_automatica_crear_y_actualizar(client: AsyncClient):
    headers = _headers_admin()

    crear_resp = await client.post(
        "/api/v1/productos",
        headers=headers,
        json={"codigo": "P001", "nombre": "Arroz superior", "categoria": "Abarrotes", "unidad_id": 1},
    )
    assert crear_resp.status_code == 201, crear_resp.text
    producto_id = crear_resp.json()["producto_id"]

    auditoria_tras_crear = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id}
    )
    assert auditoria_tras_crear.status_code == 200
    items_crear = auditoria_tras_crear.json()["items"]
    assert len(items_crear) == 1
    assert items_crear[0]["accion"] == "CREAR"
    assert items_crear[0]["entidad"] == "producto"
    assert items_crear[0]["entidad_id"] == producto_id
    assert items_crear[0]["usuario_id"] == 1  # _headers_admin usa usuario_id=1

    actualizar_resp = await client.patch(
        f"/api/v1/productos/{producto_id}", headers=headers, json={"nombre": "Arroz superior premium"}
    )
    assert actualizar_resp.status_code == 200, actualizar_resp.text

    auditoria_tras_actualizar = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id}
    )
    items_actualizar = auditoria_tras_actualizar.json()["items"]
    assert len(items_actualizar) == 2
    acciones = {item["accion"] for item in items_actualizar}
    assert acciones == {"CREAR", "ACTUALIZAR"}

    # otra entidad no aparece en el filtro
    auditoria_otra_entidad = await client.get(
        "/api/v1/auditoria", headers=headers, params={"entidad": "producto", "entidad_id": producto_id + 999}
    )
    assert auditoria_otra_entidad.json()["items"] == []
