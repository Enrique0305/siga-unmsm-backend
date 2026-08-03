# SIGA-UNMSM — Backend (FastAPI)

Sistema Integral de Gestión de Almacén y Abastecimiento Alimentario,
Universidad Nacional Mayor de San Marcos. Este repo arranca con el
**backend completo primero**; el frontend en Next.js se agrega después
(ver `frontend/README.md`).

## Stack

- **FastAPI** + **SQLAlchemy 2.0 (async)** + **aiomysql**
- **MySQL 8.0** (esquema y reglas de negocio ya definidos en `db/init/`)
- **Alembic** para migraciones futuras (el esquema base se creó por SQL directo, no por Alembic — ver nota abajo)
- **JWT** (access + refresh) con RBAC por rol y alcance por almacén (RN-20)
- **Docker Compose** para levantar todo con un solo comando

## Arranque rápido

```bash
cp .env.example .env
# Edita .env: como mínimo cambia SECRET_KEY (openssl rand -hex 32)

docker compose up --build
```

Esto levanta:
- `mysql` en `localhost:3306` — al primer arranque (volumen vacío) ejecuta
  automáticamente, en orden:
  1. `db/init/01_schema.sql` — las 60 tablas + triggers válidos
  2. `db/init/02_patch_trigger.sql` — reemplaza el trigger auto-referenciado
     de `alimento_version` por el índice único generado (evita Error 1442)
  3. `db/init/03_carga_catalogo_nutricional.sql` — 1,870 alimentos de la
     Tabla Peruana de Composición de Alimentos (Colegio de Nutricionistas)
- `api` en `localhost:8000` — docs interactivas en `http://localhost:8000/api/v1/docs`

### Sellar Alembic y sembrar datos base

La primera vez, con los contenedores corriendo:

```bash
# Le dice a Alembic "el esquema ya existe, este es el punto de partida"
docker compose exec api alembic stamp head

# Crea roles, sedes, los 4 almacenes y el usuario admin inicial
docker compose exec api python -m app.seed
```

El seed imprime el correo/contraseña temporal del administrador — cámbiala
apenas inicies sesión.

## Módulos implementados hasta ahora

| Módulo | Endpoints | Estado |
|---|---|---|
| Autenticación | `POST /auth/login`, `POST /auth/refresh` | ✅ |
| Usuarios | `GET/POST /usuarios`, `GET /usuarios/me` | ✅ |
| Almacenes | `GET/POST/PATCH /almacenes` (con alcance RN-20) | ✅ |
| Catálogos base | `GET /catalogos/categorias-alimento`, `/unidades-medida` | ✅ |
| Catálogo nutricional | `GET/POST /alimentos`, `POST /alimentos/{id}/versiones` (versionado RN-25/26) | ✅ |
| Recetas (Módulo 1A) | `GET/POST /recetas`, `/recetas/{id}/estado`, `/recetas/{id}/versiones`, `/recetas/{id}/recalcular-nutricion` | ✅ |
| Planificación / Menús (Módulo 1A) | `raciones-anuales`, `menus-quincenales`, `dias`, `dias/{id}/platos` (RN-22) | ✅ |
| Dosificación / BOM automático (Módulo 1A) | `POST/GET /planificacion/dias/{id}/dosificacion` | ✅ |
| Contratos / Proveedores (Módulo 2) | — | ⏳ siguiente |
| Compras / OC (Módulo 3) | — | ⏳ |
| Inspección / Actas | — | ⏳ |
| Kardex / Bin Card / Transferencias | — | ⏳ |
| Cocina / Consumo (Módulo 4) | — | ⏳ |
| Conformidad / Pagos (Módulo 5) | — | ⏳ |
| Reportes / Auditoría | — | ⏳ |

Cada módulo nuevo sigue el mismo patrón ya establecido:
`app/models/<modulo>.py` → `app/schemas/<modulo>.py` → `app/crud/<modulo>.py`
→ `app/api/v1/<modulo>.py` → registrar en `app/api/v1/router.py`.

## Desarrollo sin Docker (alternativa)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Ajusta DATABASE_URL en .env para apuntar a tu MySQL local
uvicorn app.main:app --reload
```

## Tests

```bash
docker compose exec api pytest
```

## Decisiones de arquitectura relevantes

- **RBAC + alcance por almacén va en el JWT**, no se re-consulta la BD en
  cada request (ver `core/security.py` y `api/deps.py`).
- **Nada de triggers auto-referenciados en MySQL** (ver el problema
  documentado en `db/init/02_patch_trigger.sql`): la regla "una sola
  versión vigente por alimento" se garantiza con una columna generada +
  índice único, no con un trigger.
- **Versionado inmutable**: `alimento_version` nunca se actualiza in-place;
  corregir valores nutricionales siempre crea una fila nueva (mismo patrón
  se usará para `receta` cuando se implemente Planificación/Recetas).
