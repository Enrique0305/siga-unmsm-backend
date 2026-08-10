# SIGA-UNMSM — Backend (FastAPI) + Frontend (Next.js)

Sistema Integral de Gestión de Almacén y Abastecimiento Alimentario,
Universidad Nacional Mayor de San Marcos. Cubre el ciclo completo:
planificación nutricional anual → contratación de proveedores → compras
mensuales → recepción e inspección → control de inventario multialmacén
→ distribución a cocina → conformidad y pago, más reportes/auditoría
transversales y jobs automáticos.

**Backend y frontend están completos** (los 5 módulos de negocio +
Reportes/Auditoría/Administración, tanto API como pantallas). El
historial detallado de cada sesión de desarrollo, decisiones de diseño y
gotchas ya resueltos vive en `CLAUDE.md` (raíz del repo) — léelo antes de
tocar código, evita reintroducir bugs ya corregidos.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 (async, `aiomysql`) + Pydantic v2
  + JWT (access/refresh) con RBAC por rol y alcance por almacén (RN-20) +
  APScheduler (jobs diarios in-process, RN-11/RN-12)
- **Base de datos:** MySQL 8.0 — esquema completo (~60 tablas) ya definido
  en `db/init/`
- **Frontend:** Next.js 16 (App Router, TypeScript, Tailwind v4) — cliente
  API generado desde el OpenAPI del backend (`orval`), ver
  `frontend/README.md`
- **Alembic** para migraciones futuras (el esquema base se creó por SQL
  directo, no por Alembic — ver nota abajo)
- **Docker Compose** para levantar los 3 servicios (`mysql`, `api`,
  `frontend`) con un solo comando

## Arranque rápido

```bash
cp .env.example .env
# Edita .env: como mínimo cambia SECRET_KEY (openssl rand -hex 32)

docker compose up --build
```

Esto levanta:
- `mysql` en `localhost:3306` — al primer arranque (volumen vacío) ejecuta
  automáticamente, en orden, todo `db/init/`:
  1. `01_schema.sql` — las ~60 tablas del esquema completo
  2. `03_carga_catalogo_nutricional.sql` — 1,870 alimentos de la Tabla
     Peruana de Composición de Alimentos (Colegio de Nutricionistas)
- `api` en `localhost:8000` — docs interactivas en
  `http://localhost:8000/api/v1/docs`
- `frontend` en `localhost:3000`

Si tu base de datos se creó con una versión de `01_schema.sql` anterior a
algún fix reciente, `db/patches_historicos/` tiene los `ALTER`/`CREATE
TABLE` correspondientes con instrucciones (no hace falta correrlos sobre
una base creada por un `docker compose up` reciente — ya están incluidos
en `01_schema.sql`).

### Sellar Alembic y sembrar datos base

La primera vez, con los contenedores corriendo:

```bash
# Le dice a Alembic "el esquema ya existe, este es el punto de partida"
docker compose exec api alembic stamp head

# Crea los 8 roles, las 3 sedes, los 4 almacenes reales, un centro de
# consumo por almacén, 4 unidades de medida base y el usuario admin
docker compose exec api python -m app.seed
```

El seed imprime el correo/contraseña temporal del administrador — cámbiala
apenas inicies sesión.

## Producción

`docker-compose.yml` está pensado para **desarrollo** (hot-reload: monta
el código fuente como volumen y corre `next dev`/`uvicorn --reload`). Para
producción usa `docker-compose.prod.yml`, que:

- construye el frontend con `frontend/Dockerfile.prod` (build optimizado
  de Next.js — `output: "standalone"` — sin servidor de desarrollo);
- corre la API sin `--reload` y sin montar el código como volumen (usa el
  código ya copiado en la imagen);
- **no publica el puerto de MySQL (3306)** al host — solo accesible entre
  contenedores del propio compose.

```bash
cp .env.example .env
# SECRET_KEY real (openssl rand -hex 32), MYSQL_PASSWORD/MYSQL_ROOT_PASSWORD
# reales (no los de ejemplo), BACKEND_CORS_ORIGINS con el dominio real del
# frontend, ENVIRONMENT=production

docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec api alembic stamp head
docker compose -f docker-compose.prod.yml exec api python -m app.seed
```

**Pendiente, fuera del alcance de este compose** (requiere un dominio y
certificado reales, no se puede resolver de forma genérica): un proxy
inverso con TLS (Nginx/Caddy/Traefik) delante de la API (puerto 8000) y
el frontend (puerto 3000) — hoy ambos quedan en HTTP plano. Si vas a
correr esto expuesto a internet, no lo hagas sin ese proxy delante.

## Módulos implementados

| Módulo | Descripción | Estado |
|---|---|---|
| Autenticación | JWT access/refresh, RBAC | ✅ |
| Usuarios / Roles | CRUD + alcance por almacén (RN-20) y por proveedor | ✅ |
| Almacenes / Catálogos | Almacenes, sedes, centros de consumo, catálogos base | ✅ |
| Catálogo nutricional (1A) | Alimentos versionados (RN-25/26) | ✅ |
| Recetas (1A) | RN-22/23/25/26, máquina de estados, versionado | ✅ |
| Planificación / Menús (1A) | Ración anual, menú quincenal, platos (RN-22) | ✅ |
| Dosificación / BOM (1A) | Cálculo automático (RN-24) + consolidación a Requerimiento Anual (RN-28) | ✅ |
| Proveedores / Contratos (2) | Saldo físico/monetario global (RN-01/19), alertas de vigencia/saldo (RN-12) | ✅ |
| Compras (3) | Orden de compra multialmacén, pedido semanal, guía de remisión (RN-01/02/03/09/13/15/16/19) | ✅ |
| Inspección / Actas | Conforme/observado, subsanación, reinspección (RN-04/05/11) | ✅ |
| Almacén | Ingresos, stock/kardex/bin card (RN-06), ajustes, mermas, devoluciones, inventarios físicos, transferencias (RN-18) | ✅ |
| Cocina / Consumo (4) | Solicitud + nota de salida, stock comprometido (RN-07/17/21) | ✅ |
| Conformidad / Pagos (5) | Cierre de OC, informe de conformidad, penalidades (RN-05/10) | ✅ |
| Auditoría | Evento automático por entidad (RN-08), con diff de columnas | ✅ |
| Reportes | Valorización, comparativo de consumo, alertas (stock/vencimiento/observaciones) | ✅ |
| Administración | Usuarios, productos, catálogos, parámetros del sistema | ✅ |
| Notificaciones | RN-12, generadas por job automático | ✅ |
| Jobs automáticos | RN-11 (cierre por plazo vencido) y RN-12 (alertas de contrato), APScheduler diario | ✅ |

Cada módulo sigue el mismo patrón:
`app/models/<modulo>.py` → `app/schemas/<modulo>.py` → `app/crud/<modulo>.py`
→ `app/api/v1/<modulo>.py` → registrar en `app/api/v1/router.py`. Ver
sección 3 de `CLAUDE.md` para las convenciones exactas.

## API para consumidores externos

Toda la API es JWT-only — no hay ningún endpoint público en todo el
backend. Un sistema externo que quiera consumir un recurso tiene que
autenticarse igual que el frontend.

### Autenticación

```
POST /api/v1/auth/login
Content-Type: application/json

{ "correo": "...", "password": "..." }
```

Devuelve `access_token` (vida corta, `ACCESS_TOKEN_EXPIRE_MINUTES` en
`.env`, default 30 min) y `refresh_token`. Para una integración de larga
duración, guardá el `refresh_token` y pedí uno nuevo vía
`POST /api/v1/auth/refresh` cuando expire, en vez de loguear en cada
llamada.

**Usuario dedicado, no el admin:** para cualquier integración externa,
creá un usuario propio con el rol menos privilegiado que alcance
(`POST /api/v1/usuarios`, rol `ADMIN`-only) — por ejemplo `COCINA` sin
`almacen_ids` asignados si solo necesita leer catálogos/menús: no puede
escribir en ningún módulo (RN-20 bloquea cualquier operación sobre
almacenes que no tenga asignados), y queda aislado de la cuenta admin
real. Ver la lista de roles en la sección 4 de `CLAUDE.md`.

### `GET /planificacion/menu-diario` — menú del día

Pensado específicamente para consumo externo (ej. una pantalla de cocina,
una app de comensales) — resuelve en una sola llamada lo que internamente
son 3 tablas relacionadas (`RacionAnual` → `MenuQuincenal` →
`MenuDia`/`Plato`).

```
GET /api/v1/planificacion/menu-diario?fecha=2026-09-03&centro_consumo_id=1
Authorization: Bearer <access_token>
```

| Parámetro | Tipo | Requerido |
|---|---|---|
| `fecha` | `YYYY-MM-DD` | sí |
| `centro_consumo_id` | int — ver `GET /api/v1/catalogos/centros-consumo` | sí |

Devuelve una lista (puede haber más de una fila por día — DESAYUNO,
ALMUERZO, CENA son filas separadas):

```json
[
  {
    "menu_dia_id": 12,
    "menu_id": 3,
    "fecha": "2026-09-03",
    "tipo_servicio": "ALMUERZO",
    "raciones_programadas": 100,
    "platos": [
      { "plato_id": 5, "receta_id": 7, "receta_nombre": "Arroz con pollo", "raciones_override": null }
    ]
  }
]
```

Solo mira el `MenuQuincenal` en estado `VIGENTE` — un borrador/en revisión
todavía puede cambiar, así que no es "el" menú real de ese día para un
consumidor externo. Si no hay menú vigente para esa fecha/centro, devuelve
`[]` (200), nunca un error.

## Frontend

El frontend Next.js cubre las pantallas de los 17 módulos de arriba
(CRUD, máquinas de estado, formularios anidados, reportes). Ver
`frontend/README.md` para arquitectura (patrón BFF, cliente `orval`) y
arranque.

## Desarrollo sin Docker (alternativa)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
# Ajusta DATABASE_URL en .env para apuntar a tu MySQL local
uvicorn app.main:app --reload
```

## Tests

```bash
docker compose exec api pytest
# o, sin Docker, desde backend/ con el venv activo:
pytest -q
```

La suite corre contra **SQLite en memoria** (no requiere MySQL corriendo)
— `Base.metadata.create_all()` + override de `get_db` + `httpx.AsyncClient`
contra la app real. Cubre los 17 módulos de arriba en 13 archivos
`tests/test_*.py`.

## Decisiones de arquitectura relevantes

- **RBAC + alcance por almacén/proveedor va en el JWT**, no se re-consulta
  la BD en cada request (ver `core/security.py` y `api/deps.py`).
- **Nada de triggers auto-referenciados en MySQL** (un trigger no puede
  modificar la misma tabla que lo disparó): reglas tipo "una sola fila
  vigente por grupo" se garantizan con una columna generada + índice
  único, no con un trigger — ver `db/init/02_patch_trigger.sql` y la
  sección 6 de `CLAUDE.md`.
- **Versionado inmutable**: `alimento_version` y `receta` nunca se
  actualizan in-place; corregir valores crea una fila nueva (RN-25).
- **`kardex_movimiento`/`bin_card_movimiento` son insert-only** (RN-06) —
  toda escritura de stock pasa por un único helper central
  (`crud/stock.py::registrar_movimiento`) que mantiene el saldo corrido y
  el costo promedio ponderado en sincronía.
- **Auditoría automática** (RN-08): un evento SQLAlchemy global
  (`core/audit.py`) registra cada `CREAR`/`ACTUALIZAR`/`ELIMINAR` de
  cualquier entidad con PK simple, sin que ningún `crud/*.py` tenga que
  llamarlo explícitamente.
- **Jobs automáticos in-process** (APScheduler vía el `lifespan` de
  FastAPI, `core/scheduler.py`) — sin worker separado, pensado para una
  sola instancia sin réplicas.

Para el detalle completo de reglas de negocio (RN-01 a RN-28), gotchas de
MySQL/SQLAlchemy async ya resueltos, y el historial sesión por sesión de
qué se construyó y por qué, ver `CLAUDE.md`.
