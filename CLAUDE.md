# SIGA-UNMSM — Contexto del proyecto para Claude Code

> Este archivo se lee automáticamente al abrir el proyecto en Claude Code.
> Contiene todo el contexto de diseño, decisiones de arquitectura, bugs ya
> resueltos y el estado actual, para continuar el desarrollo sin repetir
> trabajo ni reintroducir errores ya corregidos.

## 1. Qué es este proyecto

**SIGA-UNMSM** — Sistema Integral de Gestión de Almacén y Abastecimiento
Alimentario para la Universidad Nacional Mayor de San Marcos. Cubre el
ciclo completo: planificación nutricional anual → contratación de
proveedores → compras mensuales → recepción e inspección → control de
inventario multialmacén → distribución a cocina → conformidad y pago.

Prioridades no negociables del diseño: **trazabilidad completa** de cada
insumo (requerimiento → contrato → OC → guía → inspección → ingreso →
salida → pago), **control presupuestal** contractual, y **auditoría**
(nada se sobrescribe ni se borra; todo cambio relevante queda versionado
o registrado).

## 2. Stack técnico

- **Backend:** FastAPI + SQLAlchemy 2.0 (async, `aiomysql`) + Pydantic v2 + JWT (access/refresh) + Alembic
- **Base de datos:** MySQL 8.0 (el esquema completo, ~60 tablas, ya existe — ver sección 5)
- **Frontend:** Next.js — **aún no iniciado**, es el siguiente gran bloque después de terminar el backend
- **Infraestructura:** Docker Compose (`mysql` + `api` + placeholder `frontend` comentado en `docker-compose.yml`)

## 3. Patrón de código establecido (seguir siempre este orden)

Cada módulo nuevo se construye en este orden, replicando el patrón de los
módulos ya hechos (`alimento`, `receta`, `planificacion` son las mejores
referencias):

```
app/models/<modulo>.py     → clases SQLAlchemy (Mapped/mapped_column, SQLAlchemy 2.0 style)
app/schemas/<modulo>.py    → Pydantic v2 (Create / Out / Update, con ConfigDict(from_attributes=True))
app/crud/<modulo>.py       → repositorio: hereda de CRUDBase, agrega métodos específicos + reglas RN-xx
app/api/v1/<modulo>.py     → endpoints FastAPI, usa Depends(get_current_user) / require_roles(...)
app/api/v1/router.py       → registrar el nuevo router aquí (api_router.include_router(...))
app/models/__init__.py     → importar el modelo nuevo aquí (necesario para que SQLAlchemy resuelva relaciones)
```

Reglas de estilo ya usadas en todo el código:
- Nombres de tablas/columnas en **español**, snake_case, igual que el SQL.
- Todo endpoint de lectura requiere `Depends(get_current_user)` como mínimo.
- Todo endpoint de escritura usa `Depends(require_roles("ADMIN", "..."))`.
- Los endpoints que operan sobre un almacén específico deben validar
  `current.tiene_acceso_almacen(almacen_id)` (RN-20) — ver `api/deps.py`.
- Paginación: usar `Page[T]` de `schemas/common.py` y `CRUDBase.list_paginated`.
- Cuando un schema de salida necesita datos de una relación (ej. nombre de
  un alimento dentro de un ingrediente), **no confiar en el mapeo
  automático `from_attributes`** para relaciones anidadas con campos
  renombrados — construir la respuesta explícitamente con un
  `@classmethod from_model(cls, obj)` (ver `RecetaIngredienteOut`,
  `PlatoOut`, `DosificacionDetalleOut` como ejemplos).

## 4. Roles del sistema (usar EXACTAMENTE estos nombres en `require_roles(...)`)

`ADMIN`, `NUTRICION`, `LOGISTICA_CENTRAL`, `ALMACENERO`, `INSPECTOR`,
`COCINA`, `PAGOS`, `PROVEEDOR`. Los roles `ADMIN`, `LOGISTICA_CENTRAL` y
`PAGOS` tienen `acceso_todos_almacenes=True` (ven todos los almacenes sin
necesidad de estar en `usuario_almacen_acceso`); el resto solo ve los
almacenes que tenga asignados explícitamente (RN-20).

## 5. Base de datos: dónde está cada cosa

El esquema (DDL) vive en `db/init/`, se ejecuta automáticamente al primer
`docker compose up` (contenedor MySQL vacío):

1. `01_schema.sql` — las ~60 tablas, ya con todos los fixes aplicados (ver sección 6)
2. `02_patch_trigger.sql` — ya integrado en 01, se deja por trazabilidad histórica
3. `03_carga_catalogo_nutricional.sql` — 1,870 alimentos de la Tabla Peruana de Composición de Alimentos (Colegio de Nutricionistas del Perú)

**Regla de oro:** el ORM (`app/models/*.py`) SOLO mapea tablas que ya
existen en `01_schema.sql`. Nunca se usa `Base.metadata.create_all()`
contra MySQL. Si un modelo nuevo necesita una tabla que no existe:
1. Agregar el `CREATE TABLE` a `db/init/01_schema.sql` (para instalaciones nuevas)
2. Si ya hay una base corriendo con datos, escribir también un script de
   parche `NN_parche_<algo>.sql` con el `ALTER TABLE` correspondiente
   (mismo patrón que `09_parche_password_usuario.sql` y
   `10_parche_receta_codigo_version.sql`)

Migraciones futuras de esquema: usar Alembic (`alembic revision
--autogenerate`), NO editar `01_schema.sql` a mano salvo para el
bootstrapping inicial de un módulo nuevo.

## 6. Gotchas de MySQL ya descubiertos — NO repetir estos errores

1. **Un trigger NO puede modificar la misma tabla que lo disparó**
   (Error 1442: *"Can't update table ... in stored function/trigger
   because it is already used by statement which invoked this stored
   function/trigger"*). Para reglas tipo "solo una fila activa/vigente
   por grupo", usar el patrón de `alimento_version.vigente_key`: una
   columna generada (`GENERATED ALWAYS AS (IF(condicion, id, NULL))
   STORED`) + índice único sobre esa columna (MySQL permite múltiples
   `NULL` en un índice único). Nunca un trigger self-referencial.

2. **MySQL analiza pero IGNORA una cláusula `REFERENCES` escrita dentro
   de la definición de columna** (`col INT REFERENCES tabla(col)`) — no
   crea ninguna FK real, aunque el CREATE TABLE no dé error. Siempre usar
   `CONSTRAINT nombre FOREIGN KEY (col) REFERENCES tabla(col)` como
   cláusula de tabla explícita, o Workbench (y cualquier herramienta de
   reverse-engineering) mostrará las tablas sin relaciones.

3. **Cuidado con columnas UNIQUE que en realidad deberían ser UNIQUE
   compuesto.** Ya pasó con `receta.codigo` (debía ser
   `UNIQUE(codigo, version)`, no `UNIQUE(codigo)`, porque el versionado
   de RN-25 crea una fila nueva con el mismo código). Antes de poner
   `UNIQUE` en una columna, preguntarse: "¿este valor se repetirá
   legítimamente en un escenario de versionado/multialmacén/histórico?"

4. **`DATETIME` en vez de `TIMESTAMP`** para casi todo (evita el límite
   de rango 2038 y el auto-update implícito de `TIMESTAMP` en MySQL).

## 7. Gotchas de SQLAlchemy async ya descubiertos

1. **Nunca dejar que una relación se cargue de forma perezosa
   (`lazy="select"`, el default) en un `await`.** El driver async no
   soporta I/O implícito en medio de un acceso a atributo. Siempre
   `selectinload(...)` explícito en la query, o `lazy="joined"` en la
   definición del modelo si la relación se necesita casi siempre (ver
   `Usuario.rol`, `RecetaIngrediente.alimento`).

2. **Cuidado con el mapa de identidad de la sesión y relaciones
   cacheadas en `None`.** Si cargas un objeto con
   `selectinload(Padre.hijo)` ANTES de que la fila del hijo exista,
   `padre.hijo` queda cacheado como `None` en esa sesión, y crear el hijo
   después NO actualiza automáticamente ese atributo — hay que
   `await db.refresh(padre, attribute_names=["hijo"])` explícitamente
   tras el insert. Ya pasó con `Receta.valor_nutricional` en
   `crud/receta.py::recalcular_nutricion` — el fix está comentado ahí
   mismo, usarlo como referencia si aparece un bug similar.

## 8. Reglas de negocio (RN-01 a RN-28) — resumen de referencia

El detalle completo de cada regla, con su flujo, está en
`docs/01_diseno_sistema_SIGA-UNMSM.md` (si no está en el repo, pedirlo).
Resumen para no tener que abrir el documento a cada rato:

**Compras/contratos:** RN-01 (saldo contractual físico/monetario antes de
emitir OC) · RN-02 (guía siempre ligada a OC + pedido semanal) · RN-03
(cantidad ingresada ≤ solicitada salvo autorización) · RN-09 (precio de OC
= precio vigente del contrato, no editable) · RN-19 (saldo contractual es
GLOBAL, no por almacén).

**Calidad/almacén:** RN-04 (solo conforme ingresa a stock) · RN-05
(observado no genera conformidad hasta subsanar) · RN-06 (kardex/bin card
insert-only, nunca UPDATE/DELETE) · RN-07 (nota de salida requiere stock
disponible suficiente) · RN-08 (todo documento: numeración, estado,
responsable, fecha, adjuntos, auditoría).

**Multialmacén:** RN-13 (guía siempre indica almacén destino) · RN-14
(ingreso solo actualiza el almacén receptor) · RN-15 (suma de distribución
por almacén = cantidad total de la línea de OC) · RN-16 (pedido semanal
por combinación única sede+menú+almacén) · RN-17 (nota de salida solo
descuenta el almacén de la cocina solicitante) · RN-18 (transferencia:
salida ≠ ingreso hasta confirmar recepción) · RN-20 (alcance de usuario
por almacén) · RN-21 (disponible = físico − comprometido).

**Nutrición/recetas (Módulo 1A, ya implementado):** RN-22 (solo receta
VIGENTE entra a un menú) · RN-23 (≥1 ingrediente y rendimiento>0) · RN-24
(fórmula de dosificación) · RN-25 (versionado inmutable, nunca editar una
receta aprobada/vigente) · RN-26 (solo Nutricionista/Admin edita catálogo
o recetas) · RN-27 (pedido semanal separado por almacén+comedor) · RN-28
(alerta si dosificación > stock/saldo, no bloquea).

## 9. Estado actual — qué ya está construido y probado

| Módulo | Archivos | Endpoints | Tests |
|---|---|---|---|
| Auth (JWT access/refresh) | `models/usuario.py`, `api/v1/auth.py` | `POST /auth/login`, `/auth/refresh` | ✅ |
| Usuarios | `crud/usuario.py`, `api/v1/usuarios.py` | `GET/POST /usuarios`, `GET /usuarios/me` | ✅ |
| Almacenes (RN-20) | `models/organizacion.py`, `api/v1/almacenes.py` | `GET/POST/PATCH /almacenes` | ✅ |
| Catálogos base | `api/v1/catalogos.py` | `/catalogos/categorias-alimento`, `/unidades-medida` | ✅ |
| Catálogo nutricional (RN-25/26) | `models/catalogos.py`, `crud/alimento.py` | `GET/POST /alimentos`, `POST /alimentos/{id}/versiones` | ✅ |
| Recetas (RN-22/23/25/26) | `models/receta.py`, `crud/receta.py`, `api/v1/recetas.py` | CRUD + `/estado` + `/versiones` + `/recalcular-nutricion` | ✅ `tests/test_recetas.py` |
| Planificación/Menús | `models/planificacion.py`, `crud/planificacion.py` | raciones-anuales, menus-quincenales, dias, platos | ✅ |
| Dosificación/BOM automático (RN-24/27/28) | `models/dosificacion.py`, `crud/dosificacion.py` | `POST/GET /planificacion/dias/{id}/dosificacion` | ✅ |

**Seed inicial:** `app/seed.py` crea los 8 roles, las 3 sedes, los 4
almacenes reales y el usuario admin (`docker compose exec api python -m
app.seed`).

**Patrón de testing:** SQLite en memoria + `Base.metadata.create_all()` +
override de la dependencia `get_db` + `httpx.AsyncClient` contra la app
real (ver `tests/test_recetas.py` como plantilla completa). No se necesita
MySQL corriendo para testear lógica de negocio.

## 10. Próximos pasos (en este orden, por dependencias)

1. **Módulo 2 — Contratos/Proveedores** (`proveedor`, `contrato`,
   `cronograma_entrega`, `producto_contratado` — saldo físico/monetario
   GLOBAL, alertas RN-12 de vencimiento/saldo bajo)
2. **Módulo 3 — Compras** (`orden_compra` + `orden_compra_distribucion`
   multialmacén con RN-01/RN-15, `pedido_semanal`, `guia_remision`)
3. **Inspección/Actas** (`inspeccion`, `acta_observacion`, `subsanacion` — RN-04/05)
4. **Almacén** (`ingreso_almacen`, `kardex_movimiento`/`bin_card_movimiento`
   insert-only RN-06, `stock_almacen_producto`, `transferencia_almacen` RN-18,
   `ajuste_inventario`/`merma`/`devolucion`/`inventario_fisico`)
5. **Módulo 4 — Cocina/Consumo** (`solicitud_cocina`, `nota_salida` — RN-07/17,
   comparar consumo real vs. teórico usando `dosificacion_detalle` ya calculado)
6. **Módulo 5 — Conformidad/Pagos** (`penalidad`, `informe_conformidad_pago`)
7. **Reportes y auditoría** (usar `auditoria_log`, ya existe la tabla —
   falta decidir si se llena vía middleware/evento SQLAlchemy o
   explícitamente en cada servicio)
8. **Frontend Next.js** — recién después de cerrar el backend completo

## 11. Cómo correr el proyecto

Ver `README.md` en la raíz — resumen: `cp .env.example .env` → cambiar
`SECRET_KEY` → `docker compose up --build` → (primera vez)
`docker compose exec api alembic stamp head && docker compose exec api
python -m app.seed`. Docs interactivas en
`http://localhost:8000/api/v1/docs`.
