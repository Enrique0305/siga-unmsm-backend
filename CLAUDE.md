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
- **Frontend:** Next.js 16 (App Router, TypeScript, Tailwind v4) — Sesión 1 completa (auth + shell + Dashboard), ver `frontend/README.md` y sección 12
- **Infraestructura:** Docker Compose (`mysql` + `api` + `frontend`, los 3 servicios activos en `docker-compose.yml`)

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

3. **Columnas `GENERATED ALWAYS ... STORED` (ej. `producto_contratado.
   tope_monetario`) se mapean con `mapped_column(Computed("expr",
   persisted=True))`**, nunca como columna normal (el ORM no debe
   escribirlas). Tras el `INSERT`, SQLAlchemy deja ese atributo
   "expirado" — leerlo sin refrescar antes dispara I/O implícito y revienta
   en async igual que el gotcha #1. Hacer `await db.flush()` seguido de
   `await db.refresh(obj)` antes de devolver el objeto (ver
   `crud/contrato.py::agregar_producto_contratado`); si el modelo tiene
   además una relación `lazy="joined"`, el mismo `refresh()` sin
   `attribute_names` la recarga de paso.

4. **PK `BIGINT AUTO_INCREMENT` (ej. `kardex_movimiento.kardex_id`,
   `bin_card_movimiento.bin_card_id`) mapeada como `mapped_column(BigInteger,
   primary_key=True)` revienta en los tests con SQLite** (`NOT NULL
   constraint failed` al insertar): SQLite solo convierte una columna en
   alias del `rowid` (con autoincremento real) cuando su tipo declarado es
   exactamente `INTEGER`, no `BIGINT`. Como los tests corren
   `Base.metadata.create_all()` contra SQLite (nunca contra MySQL, ver
   sección 9), hay que declarar
   `mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)`
   — en MySQL sigue siendo `BIGINT`, en SQLite se crea como `INTEGER` y
   autoincrementa. Está centralizado como `BigIntPK` en `db/base.py`
   (se usó dos veces — `models/inventario.py` y `models/auditoria.py` —
   así que se promovió ahí en vez de duplicarlo una tercera vez);
   importar de ahí para cualquier PK `BIGINT` nueva.

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
| Planificación/Menús (RacionAnual + MenuQuincenal + MenuDia/Plato, RN-22) | `models/planificacion.py`, `crud/planificacion.py` (`CRUDRacionAnual`/`CRUDMenuQuincenal` con `TRANSICIONES_VALIDAS_RACION`/`_MENU`) | `raciones-anuales` CRUD (sin Update) + `/estado`, `menus-quincenales` CRUD (sin Update) + `/estado` + `/dias`, `dias/{id}` + `/platos` | ✅ `tests/test_planificacion.py` |
| Dosificación/BOM automático (RN-24/27/28) | `models/dosificacion.py`, `crud/dosificacion.py` | `POST/GET /planificacion/dias/{id}/dosificacion` | ✅ |
| Producto (catálogo logístico, prerrequisito Módulo 2) | `models/catalogos.py::Producto`, `crud/producto.py` | `GET/POST/PATCH /productos` | ✅ `tests/test_contratos.py` |
| Requerimiento anual (prerrequisito Módulo 2, CRUD manual sin auto-consolidación BOM) | `models/planificacion.py::RequerimientoAnual(Detalle)`, `crud/requerimiento.py` | CRUD + `/estado` (BORRADOR→EN_REVISION→APROBADO→VIGENTE) | ✅ `tests/test_contratos.py`, `tests/test_planificacion.py` |
| Módulo 2 — Proveedores/Contratos (RN-12/19) | `models/contratos.py`, `crud/proveedor.py`, `crud/contrato.py` | `/proveedores`, `/contratos` + `/estado` + `/cronograma` + `/productos` | ✅ `tests/test_contratos.py` |
| Módulo 3 — Compras (RN-01/02/03/09/13/15/16/19) | `models/compras.py` (incl. `AutorizacionExcedente`), `crud/orden_compra.py`, `crud/pedido_semanal.py`, `crud/guia_remision.py` | `/ordenes-compra` + `/estado` + `/detalle/{id}/autorizaciones-excedente`, `/pedidos-semanales`, `/guias-remision` + `/detalle` | ✅ `tests/test_compras.py` |
| Inspección/Actas (RN-04/05/11, dueño de `guia_remision.estado`) | `models/inspeccion.py`, `crud/inspeccion.py`, `crud/acta_observacion.py` | `/inspecciones`, `/actas-observacion` + `/desde-inspeccion-detalle/{id}` + `/subsanaciones` + `/subsanaciones/{id}/reinspeccion` | ✅ `tests/test_inspeccion.py` |
| Almacén — Ingresos/Stock/Kardex/Ajustes/Transferencias (RN-04/06/18/20) | `models/organizacion.py::UbicacionInterna`, `models/inventario.py`, `crud/stock.py` (helper central `registrar_movimiento`) | `/ubicaciones`, `/ingresos-almacen`, `/stock-almacen`, `/kardex`, `/ajustes-inventario`, `/mermas`, `/devoluciones`, `/inventarios-fisicos` + `/cerrar`, `/transferencias` + `/recepcion` | ✅ `tests/test_almacen.py` |
| Módulo 4 — Cocina/Consumo (RN-07/17/20/21, activa `stock_comprometido`) | `models/cocina.py`, `crud/solicitud_cocina.py`, `crud/nota_salida.py` | `/solicitudes-cocina` + `/estado`, `/notas-salida` | ✅ `tests/test_cocina.py` |
| Módulo 5 — Conformidad y Pagos (RN-05/10, cierra `orden_compra`) | `models/pagos.py`, `crud/informe_conformidad.py`, `crud/penalidad.py` | `PATCH /ordenes-compra/{id}/estado` (`CERRADO`), `/penalidades`, `/informes-conformidad-pago` + `/estado` | ✅ `tests/test_pagos.py` |
| Auditoría automática (RN-08, evento global, todos los modelos) | `models/auditoria.py`, `core/audit.py` (evento `after_flush` + `ContextVar`), `api/middleware.py` | `GET /auditoria?entidad=&entidad_id=` | ✅ `tests/test_auditoria.py` |
| Reportes transversales | `crud/reportes.py` | `GET /reportes/valorizacion-inventario`, `/comparativo-consumo`, `/alertas` | ✅ `tests/test_reportes.py` |

**Seed inicial:** `app/seed.py` crea los 8 roles, las 3 sedes, los 4
almacenes reales y el usuario admin (`docker compose exec api python -m
app.seed`).

**Patrón de testing:** SQLite en memoria + `Base.metadata.create_all()` +
override de la dependencia `get_db` + `httpx.AsyncClient` contra la app
real (ver `tests/test_recetas.py` como plantilla completa). No se necesita
MySQL corriendo para testear lógica de negocio.

## 10. Próximos pasos (en este orden, por dependencias)

1. ~~**Módulo 2 — Contratos/Proveedores**~~ ✅ implementado (`proveedor`,
   `contrato`, `cronograma_entrega`, `producto_contratado` — saldo
   físico/monetario GLOBAL, alertas RN-12 calculadas en tiempo de consulta
   vía `Contrato.alerta_vigencia` / `ProductoContratado.alerta_saldo`, no
   hay job/cron todavía). De paso se construyeron dos prerrequisitos que no
   existían: `Producto` (catálogo logístico) y `RequerimientoAnual` (CRUD
   manual — la consolidación automática BOM → requerimiento anual sigue
   pendiente, ver punto 2).
2. ~~**Módulo 3 — Compras**~~ ✅ implementado (`orden_compra` +
   `orden_compra_distribucion` multialmacén, `pedido_semanal`,
   `guia_remision` + `guia_remision_detalle`, `autorizacion_excedente`). El
   descuento de saldo RN-01 que quedó pendiente del Módulo 2 ya se aplica
   en `crud/orden_compra.py::crear` (reserva al emitir la OC, no al recibir
   la guía — así lo especifica la sección 4.3 del diseño). RN-03 "salvo
   autorización" SÍ está implementado (`AutorizacionExcedente`,
   `POST /ordenes-compra/detalle/{id}/autorizaciones-excedente`,
   validado en `crud/guia_remision.py::_registrar_linea` contra
   `saldo_oc + total_excedente_autorizado`) — la primera versión de este
   módulo lo había marcado como "hueco del esquema" por una exploración
   incompleta de `01_schema.sql`; la tabla sí existía (sección 8, "8.
   AUTORIZACIONES DE EXCEDENTE"). Lección: al escanear el esquema para un
   módulo nuevo, revisarlo completo (`grep -n "CREATE TABLE"` sobre todo
   el archivo), no solo el bloque con el nombre del módulo. Límite que
   sigue pendiente: el rol `PROVEEDOR` no está acotado a sus propios
   documentos porque `Usuario` no tiene FK a `Proveedor`. Sigue pendiente
   cerrar la consolidación automática de `bom_consolidado` →
   `requerimiento_anual_detalle` como mejora del Módulo 1, si se necesita
   antes de escalar el uso real.
3. ~~**Inspección/Actas**~~ ✅ implementado (`inspeccion`,
   `inspeccion_detalle`, `acta_observacion`, `subsanacion`). Ahora sí es
   dueño de `guia_remision.estado`, que avanza `PENDIENTE → PARCIAL →
   CONFORME/OBSERVADO → SUBSANADO` (`crud/inspeccion.py::crear`,
   `crud/acta_observacion.py::registrar_reinspeccion`). Límite de
   alcance documentado en el propio código: `CERRADO`/`PENALIZADO`
   (guía) y el cierre de OC + `Penalidad` (RN-10/11) quedan para Módulo
   5, que es quien decide eso leyendo `acta_observacion.estado`
   (`SUBSANADA`/`RECHAZADA`); no hay job/cron para el plazo vencido de
   RN-11 (se expone `ActaObservacion.plazo_vencido` calculado, mismo
   patrón que RN-12).
4. ~~**Almacén**~~ ✅ implementado (`ingreso_almacen`, `kardex_movimiento`/
   `bin_card_movimiento` insert-only RN-06, `stock_almacen_producto`,
   `transferencia_almacen` RN-18, `ajuste_inventario`/`merma`/`devolucion`/
   `inventario_fisico`). Todas las escrituras de stock pasan por un único
   helper (`crud/stock.py::registrar_movimiento`) que mantiene
   `kardex_movimiento` y `stock_almacen_producto` en sincronía (saldo
   corrido + costo promedio ponderado) y bloquea stock físico negativo.
   `bin_card_movimiento` solo se escribe al ingresar (única tabla del
   módulo con columna de ubicación en el esquema). **Primer módulo con
   RN-20 implementado de verdad** (`deps.py::verificar_acceso_almacen`,
   para cuando `almacen_id` viene del body en vez de un path param) —
   `ALMACENERO` es `acceso_todos_almacenes=False`. Deuda técnica anotada:
   `pedidos_semanales.py` (rol `NUTRICION`) e Inspección (rol
   `INSPECTOR`) siguen sin ese chequeo pese a operar sobre recursos
   ligados a un almacén — no se tocó esos archivos ya probados, RN-20 se
   implementó recién aquí porque es donde primero importaba de verdad.
5. ~~**Módulo 4 — Cocina/Consumo**~~ ✅ implementado (`solicitud_cocina`,
   `nota_salida`). Primer módulo que activa `stock_almacen_producto.
   stock_comprometido` (`crud/stock.py::ajustar_comprometido`, helper
   simétrico a `registrar_movimiento`): la solicitud reserva contra
   `disponible = físico − comprometido` (RN-07/21), la nota de salida
   libera la reserva y recién ahí hace el movimiento real de kardex
   (`registrar_movimiento`, tipo `SALIDA`). `cantidad_teorica_bom` se
   calcula en el servidor sumando `dosificacion_detalle.cantidad_bruta_
   requerida` (ya calculada en Módulo 1A, RN-24) vía el puente
   `Producto.alimento_id`; `NotaSalidaDetalle.variacion_pct` compara
   despacho real contra ese teórico. RN-20 implementado desde el
   principio (no es deuda técnica aquí).
6. ~~**Módulo 5 — Conformidad/Pagos**~~ ✅ implementado (`penalidad`,
   `informe_conformidad_pago` + `informe_conformidad_detalle`). Este
   módulo no decide nada nuevo sobre calidad — solo **lee**
   `acta_observacion.estado` (ya fijado por Inspección) para cerrar la
   OC: `PATCH /ordenes-compra/{id}/estado` con `{"estado":"CERRADO"}`
   ahora también acepta ese target (antes solo `ANULADA`), bloqueado si
   queda alguna línea `OBSERVADO` sin acta resuelta
   (`crud/informe_conformidad.py::cerrar_orden_compra`), y crea
   `Penalidad` automática por cada acta `RECHAZADA` (monto = cantidad
   rechazada × precio de la línea — no hay fórmula de penalidad en el
   esquema, `contrato.penalidad_json` es JSON libre sin estructura
   definida, así que este es el valor por defecto más defendible sin
   inventar una interpretación arbitraria). `OrdenCompra` gana los
   estados terminales `CERRADO`/`PENALIZADO` (antes solo `EMITIDA`/
   `ANULADA`). El informe se genera una sola vez por OC ya cerrada,
   recalculando conforme/retenido por línea (RN-05: observado entra a
   pago solo si su acta quedó `SUBSANADA`) y sumando las `Penalidad` ya
   registradas. **Cierra el backend funcional completo (Módulos 1 a
   5)** — quedan pendientes los dos puntos transversales de abajo. Sin
   cron para RN-10/11 (cierre mensual masivo / plazo vencido), mismo
   hueco ya documentado para RN-12: cada OC se cierra una por una vía
   el endpoint.
7. ~~**Reportes y auditoría**~~ ✅ implementado. `auditoria_log` se
   llena con un **evento SQLAlchemy global** (`core/audit.py`,
   `@event.listens_for(Session, "after_flush")` sobre la clase base
   `Session`) — no se tocó ninguno de los ~30 `crud/*.py` existentes; el
   actor (`usuario_id`) llega vía un `contextvars.ContextVar` que
   `api/middleware.py::AuditContextMiddleware` llena por request
   decodificando el JWT (reusa `core/security.py::decode_token`, sin
   reimplementar nada) — el evento en sí no tiene forma de ver la
   request de FastAPI. Tablas con PK compuesta (`stock_almacen_producto`,
   `usuario_almacen_acceso`, etc.) no se auditan (son tablas de estado,
   no "documentos" de RN-08); `seed.py` y las siembras directas de los
   tests tampoco (sin request no hay `ContextVar`, y sin actor no hay a
   quién auditar). `detalle_json` queda `None` por ahora — enriquecerlo
   con diffs de columnas es una mejora futura, no bloqueante.
   Reportes: `GET /reportes/valorizacion-inventario`,
   `/comparativo-consumo` (BOM de Módulo 1A vs. comprado de Módulo 3 vs.
   recibido de Almacén vs. despachado de Módulo 4 — el que más tablas
   cruza) y `/alertas` (stock bajo, próximos a vencer, observaciones sin
   resolver). Límites documentados en el propio código: `/alertas` usa
   `producto.stock_minimo_referencial` como único umbral —
   `almacen_producto_parametro` (override por almacén) no tiene modelo
   en ningún módulo, no se agregó; "próximos a vencer" informa la
   cantidad *ingresada* del lote, no la que *queda* en stock hoy (el
   esquema no trackea stock por lote, solo por almacén+producto).
8. ~~**Frontend Next.js — Sesión 1**~~ ✅ implementado (scaffold, tema,
   cliente API, auth, shell, Dashboard). Ver sección 12 para arquitectura,
   decisiones y gotchas descubiertos.
   ~~**Sesión 2 — Módulo 02 Proveedores y Contratos**~~ ✅ implementado
   (CRUD completo: `/proveedores` + `/proveedores/nuevo` +
   `/proveedores/[id]/editar`, `/proveedores/contratos` +
   `/proveedores/contratos/nuevo` + `/proveedores/contratos/[id]` con
   cronograma, productos contratados y cambio de estado). Primera vez que
   un Client Component pasa por `app/api/backend/[...path]/route.ts` en
   vez de `server-fetch.ts` — encontró y corrigió un bug real de Sesión 1
   ahí (ver punto 6 abajo). Deja fijo el patrón de pantallas con
   escritura real (formularios `orval` + `useMutation`, filtros/paginación
   por searchParam, badges de estado) para replicar en las ~20 pantallas
   restantes del catálogo de la sección 3 del diseño.
   ~~**Sesión 3 — Módulo 01A Dosificación nutricional**~~ ✅ implementado
   (`/dosificacion` + `/dosificacion/nuevo` + `/dosificacion/[id]`:
   catálogo nutricional con los 21 campos de `ValorNutricional`;
   `/dosificacion/recetas` + `/dosificacion/recetas/nuevo` +
   `/dosificacion/recetas/[id]`: recetas con ingredientes anidados,
   máquina de estados, "nueva versión" y "recalcular nutrición";
   `/dosificacion/calcular`: botón de cálculo de dosificación (RN-24),
   sin pantalla de menús propia — pide `menu_dia_id`/`centro_consumo_id`
   directo por número porque el Módulo 01 de Planificación no existe
   todavía). Primera sesión donde **Receta y Alimento no tienen
   "editar"** — RN-25 los hace inmutables por diseño, solo versionado
   (`POST .../versiones`), así que no hay pantallas de edición de campos
   base, solo de corrección vía nueva versión. Verificado en el
   navegador: alimento creado → corregido (v1 queda `vigente=false`,
   v2 vigente) → receta creada con ese alimento (nutrición calculada
   automáticamente al crear) → máquina de estados completa
   `BORRADOR→EN_REVISION→APROBADO→VIGENTE` → "nueva versión" clona a un
   `receta_id` distinto en BORRADOR sin tocar el original → error 422 de
   "Centro de consumo no encontrado" en el cálculo de dosificación se
   muestra legible. Backend investigado a fondo antes de planear (3
   agentes en paralelo) porque 01 Planificación (RacionAnual/
   MenuQuincenal/Plato) tiene huecos reales — sin `GET` de detalle para
   `RacionAnual`, sin `GET` de lista/detalle ni cambio de estado para
   `MenuQuincenal` — documentados para cuando se retome esa sesión, no
   construidos aquí. `RequerimientoAnual` sí tiene CRUD completo en el
   backend pero sigue sin pantalla — queda pendiente para la sesión de
   01 Planificación.
   ~~**Sesión 4 — Módulo 01 Planificación anual**~~ ✅ implementado.
   Primera sesión full-stack (backend + frontend) — se decidió cerrar los
   huecos reales de backend detectados en la Sesión 3 antes de construir
   pantallas, en vez de acotar el frontend a lo que ya existía:
   - Backend agregado (replica el patrón exacto de `crud/requerimiento.py`):
     `GET /planificacion/raciones-anuales/{id}` + `PATCH .../estado`
     (`CRUDRacionAnual`, `TRANSICIONES_VALIDAS_RACION` — dos estados,
     `BORRADOR→APROBADO`, sin `aprobado_por_id` porque el modelo no tiene
     esa columna); `GET /planificacion/menus-quincenales` (lista) +
     `GET .../{id}` (detalle con `dias` anidado) + `PATCH .../estado`
     (`CRUDMenuQuincenal`, `TRANSICIONES_VALIDAS_MENU` — cinco estados
     `BORRADOR→EN_REVISION→APROBADO→VIGENTE→HISTORICO`, sí fija
     `aprobado_por_id`/`aprobado_en`); `GET /catalogos/sedes` y
     `/catalogos/centros-consumo` (nuevos, `schemas/almacen.py::SedeOut`/
     `CentroConsumoOut` — sin esto el formulario de `RacionAnual` no podía
     tener selects reales, hueco encontrado recién al planear el
     formulario, no en la investigación inicial). Primer testing dedicado
     de este módulo: `tests/test_planificacion.py` (antes solo se usaba
     como fixture en otros test_*.py).
   - Frontend: `/planificacion` (Raciones anuales: list/nuevo/detalle/
     estado, con selects de Sede→CentroConsumo filtrados dinámicamente en
     cliente), `/planificacion/menus` (Menús quincenales: list/nuevo/
     detalle/estado + "agregar día" inline), `/planificacion/dias/[id]`
     (MenuDia: platos + "agregar plato" inline, dropdown de recetas ya
     filtrado server-side a `estado=VIGENTE` — RN-22 se cumple por diseño
     de la UI, no solo por el 422 del backend), `/planificacion/
     requerimientos` (RequerimientoAnual: list/nuevo con detalle anidado/
     detalle/estado — primera pantalla para un backend que ya estaba
     100% completo desde el Módulo 2 pero sin UI). El detalle de un
     `MenuDia` enlaza a `/dosificacion/calcular?menu_dia_id=X` (Sesión 3)
     con el id precargado, cerrando el ciclo entre ambas sesiones.
     Verificado de punta a punta en el navegador: cadena completa de
     estados de `MenuQuincenal` y `RequerimientoAnual`, cálculo de
     dosificación disparado desde el día de menú real.
   ~~**Sesión 5 — Módulo 03 Compras**~~ ✅ implementado. A diferencia de
   las Sesiones 3 y 4, backend 100% completo desde antes (confirmado con
   un agente de exploración) — sesión puramente de frontend, con los
   hooks de `orval` ya generados desde la Sesión 1 sin usar hasta ahora.
   `/compras` (OrdenCompra: list/nuevo/detalle/estado/excedente — form de
   creación anidado 3 niveles, OC → `detalle[]` → `distribucion[]`;
   `CambiarEstadoOC` solo expone `ANULADA`/`CERRADO`, nunca `PENALIZADO`
   porque es un efecto secundario que decide Módulo 5, no una acción de
   usuario), `/compras/pedidos-semanales` (PedidoSemanal: list/nuevo/
   detalle de solo lectura — no existe endpoint `/estado` para esta
   entidad, nunca lo va a haber), `/compras/guias` (GuiaRemision: list/
   nuevo/detalle + "agregar línea" inline sobre una guía ya creada).
   Verificado de punta a punta en el navegador contra una base SQLite
   descartable: OC con una línea distribuida entre 2 almacenes (RN-15) →
   RN-15 rechazado en cliente antes de tocar el backend (distribución que
   no suma) → RN-01 rechazado por el backend (cantidad > saldo físico del
   contrato) → RN-02 verificado estructuralmente (el select de pedido
   semanal se filtra por `orden_compra_id`, así que un pedido de otra OC
   ni aparece como opción) → RN-03 rechazado (entrega > saldo) →
   autorizar excedente → reintentar la guía con esa cantidad (pasa,
   saldo mostrado como "100 + 50 exced.") → agregar línea extra a una
   guía ya creada (rechazada correctamente, saldo ya en negativo) →
   cerrar la OC (`CERRADO`, botones de estado desaparecen). **Bug real
   encontrado y corregido durante la verificación**:
   `GuiaRemisionForm.tsx` inicializaba `pedidoSemanalId` en `""` y solo lo
   poblaba dentro de `handleOrdenCompraChange` — como la OC por defecto
   ya viene preseleccionada al montar el componente (nadie dispara ese
   handler en el caso más común, crear la primera guía sin cambiar de
   OC), el `<select>` mostraba visualmente un pedido semanal válido pero
   el estado de React seguía vacío, bloqueando el submit con "Se necesita
   un pedido semanal para esta orden de compra" pese a que sí había uno.
   Fix: inicializar `pedidoSemanalId` con un lazy initializer que filtra
   `pedidosSemanales` por la OC por defecto, igual que hace
   `handleOrdenCompraChange` al cambiar de OC. **Hueco de RN-20 más amplio
   de lo documentado**: ni `ordenes_compra.py` ni `guias_remision.py`
   (además de `pedidos_semanales.py`, ya conocido) filtran por almacenes
   asignados al usuario — no se corrige en esta sesión, fuera de alcance
   (solo frontend), los selects de almacén muestran todos sin filtrar.
   ~~**Sesión 6 — Módulo "Recepción y calidad" (Inspección/Actas de
   observación/Subsanación)**~~ ✅ implementado. Backend 100% completo
   desde antes (confirmado con un agente de exploración) — sesión
   puramente de frontend, igual que la 5. `/recepcion` (Inspección:
   list/nuevo/detalle — el formulario de creación anida `detalle[]` por
   línea de guía, con validación de cliente RN-análoga a que
   `cantidad_conforme + cantidad_observada` iguale lo entregado;
   `InspeccionOut` no trae `numero_guia`, así que la lista arma un `Map`
   de lookup igual que `numeroContrato` en `compras/page.tsx`),
   `/recepcion/actas` (ActaObservacion: list/detalle — sin pantalla
   "nueva", las actas solo se crean inline desde una línea de inspección
   `OBSERVADO` vía `<CrearActaForm />`, mismo patrón que "Autorizar
   excedente" de la Sesión 5; el detalle muestra `subsanaciones[]`
   anidadas con `<AgregarSubsanacionForm />` y `<RegistrarReinspeccionForm
   />` inline, condicionadas a `estado === "ABIERTA"` y, para la
   reinspección, a que la subsanación no tenga ya un
   `resultado_reinspeccion`). Deliberadamente **no se agregó un fetch
   extra para saber si una línea de inspección ya tiene acta** —
   `InspeccionDetalleOut` no expone esa relación y el backend ya
   responde 422 con mensaje claro ante un duplicado, mismo criterio de
   "backend como autoridad" que RN-01/RN-03 en la Sesión 5 (verificado en
   el navegador: `ACTA-0002` duplicada sobre la misma línea de
   `ACTA-0001` → 422 legible). Verificado de punta a punta con dos guías
   descartables: guía 1 con línea parcialmente observada (30 conforme +
   10 observada de 40) → inspección 201, guía pasa a `OBSERVADO` → acta
   `ABIERTA` → subsanación → reinspección `CONFORME` → acta `SUBSANADA`,
   guía `SUBSANADO`; guía 2 con línea totalmente observada (0/40) → acta
   → subsanación → reinspección `NO_CONFORME` → acta `RECHAZADA`
   (terminal) pero guía **también** llega a `SUBSANADO` (la guía solo
   mira si quedan actas `ABIERTA`, no el resultado — cerrar la OC con
   penalidad es responsabilidad del Módulo 5, no de este módulo, tal
   como documenta el propio backend). Confirmado también por API (fuera
   de la UI, que ya oculta el formulario en ese estado): reintentar la
   reinspección de una subsanación ya resuelta → 422 idempotente, y
   re-inspeccionar una línea de guía ya inspeccionada → 422. Mismo hueco
   de RN-20 que Compras (ni `inspecciones.py` ni `actas_observacion.py`
   filtran por almacenes asignados al usuario) — no se corrige aquí,
   fuera de alcance (solo frontend).

## 11. Cómo correr el proyecto

Ver `README.md` en la raíz — resumen: `cp .env.example .env` → cambiar
`SECRET_KEY` → `docker compose up --build` → (primera vez)
`docker compose exec api alembic stamp head && docker compose exec api
python -m app.seed`. Docs interactivas en
`http://localhost:8000/api/v1/docs`.

## 12. Frontend (Next.js) — arquitectura y gotchas

Detalle completo en `frontend/README.md`. Resumen de las decisiones que no
son obvias leyendo el código:

1. **Next.js 16 renombró `middleware.ts` → `proxy.ts`** (función
   `middleware()` → `proxy()`, mismo `config.matcher`, misma API de
   cookies). El scaffold generado por `create-next-app` trae un
   `AGENTS.md`/`CLAUDE.md` propios (regenerados por `next dev`, no
   editarlos a mano) que avisan de leer `node_modules/next/dist/docs/`
   antes de asumir nada del training data — ya se hizo para este cambio y
   para el punto 2. El archivo del proyecto es `frontend/proxy.ts`.
2. **Tailwind v4 no usa `tailwind.config.ts`.** El tema (paleta
   institucional, fuente) se define con `@theme` directo en
   `app/globals.css` — variables `--color-primary`, `--color-warning`,
   etc. generan automáticamente las clases `bg-primary`, `text-warning`,
   etc.
3. **Patrón BFF de dos caminos**, según el tipo de componente (no hay un
   único cliente API):
   - Server Components (páginas de solo lectura) → `lib/api/server-fetch.ts`
     lee la cookie httpOnly con `next/headers` y llama a FastAPI directo.
   - Client Components (hooks `orval`/TanStack Query) → no pueden leer la
     cookie, pasan por `app/api/backend/[...path]/route.ts`, que reenvía
     con el Bearer y hace un refresh automático si FastAPI responde 401.
   - El nombre `app/api/backend/...` (no `.../proxy/...`) es deliberado:
     evita chocar con el término "Proxy" que Next.js 16 ya usa para el
     punto 1.
4. **orval con `client: 'react-query'` + `httpClient: 'fetch'` genera
   respuestas como `{ data, status, headers }`**, no el objeto plano —
   el mutator (`lib/api/mutator.ts`) tiene que devolver esa forma
   (`as T`), no solo el JSON parseado. Se confirmó corriendo
   `npm run generate:api` contra el backend real y leyendo el archivo
   generado, no asumiendo la firma de memoria.
5. **JWT decodificado sin verificar firma** en `lib/auth/session.ts` (con
   `jose`/`decodeJwt`, no `jwtVerify`) — solo para pintar rol/sidebar en
   el servidor. Es intencional: evita compartir `SECRET_KEY` entre los
   `.env` de frontend y backend; la autorización real la sigue haciendo
   FastAPI en cada request.
6. ~~**Gotcha de entorno: `passlib==1.7.4` + `bcrypt>=4.0` rompe
   `hash_password`/`verify_password`**~~ ✅ corregido — `requirements.txt`
   no fijaba versión de `bcrypt`, así que un `pip install` fresco (o una
   imagen Docker reconstruida) podía traer una versión incompatible
   (`ValueError: password cannot be longer than 72 bytes...`, falla en la
   auto-detección interna de passlib, no en la contraseña real del
   usuario). Se detectó al preparar una base SQLite descartable para
   probar el login del frontend sin Docker/MySQL disponibles en el
   entorno. Fix aplicado: `bcrypt==3.2.2` fijado explícitamente en
   `backend/requirements.txt`, verificado con reinstalación limpia +
   suite completa de tests (10/10).
7. **`app/api/backend/[...path]/route.ts` duplicaba el prefijo `/api/v1`**
   (bug real de Sesión 1, corregido en Sesión 2 al ser la primera vez que
   un Client Component pasa por esta ruta en vez de `server-fetch.ts`, que
   nunca la ejercitó). Las URLs que genera orval ya incluyen `/api/v1`
   (vienen del OpenAPI del backend, ej. `/api/v1/proveedores`), y ese
   prefijo queda capturado dentro de `path` (todo lo que sigue a
   `/api/backend/`). El handler armaba la URL final con `API_URL` (que
   YA incluye `/api/v1`) + `path.join("/")` (que TAMBIÉN incluye
   `api/v1/...`), resultando en `/api/v1/api/v1/proveedores` → 404 del
   backend. Fix: `API_ORIGIN` (origen pelado, sin `/api/v1`) para esta
   ruta específica — ver el comentario en el archivo. Lección: un camino
   de datos sin ejercitar por ninguna pantalla real puede tener bugs
   invisibles hasta la primera pantalla que sí lo usa; conviene probar
   cada camino (Server Component *y* Client Component) al menos una vez
   temprano, no asumir que "ya se probó en la sesión anterior" cubre
   ambos.
8. **Gotcha de entorno (Windows/Git Bash): `DATABASE_URL=sqlite+aiosqlite:///` con
   una ruta estilo Git Bash (`/c/Users/...`) falla con `unable to open
   database file`** — `aiosqlite`/`sqlite3` corren como proceso nativo de
   Windows y no entienden esa sintaxis de ruta traducida por Git Bash;
   hace falta una ruta Windows real (`C:/Users/...`, barras hacia adelante
   está bien, pero con letra de unidad) antes de pasarla al `DATABASE_URL`
   de la base SQLite descartable de verificación manual. `cygpath -w
   <ruta-git-bash>` la convierte. Aplica a cualquier sesión futura que
   arme un backend descartable para probar el frontend en el navegador.
