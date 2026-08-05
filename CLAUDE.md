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
| Requerimiento anual (CRUD manual + consolidación automática desde BOM, Sesión 13) | `models/planificacion.py::RequerimientoAnual(Detalle)`, `crud/requerimiento.py`, `crud/bom_consolidado.py` | CRUD + `/estado` (BORRADOR→EN_REVISION→APROBADO→VIGENTE) + `POST/GET /planificacion/raciones-anuales/{id}/consolidar-requerimiento` \| `/bom-consolidado` | ✅ `tests/test_contratos.py`, `tests/test_planificacion.py` |
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
   manual — la consolidación automática BOM → requerimiento anual quedó
   pendiente en este punto y se cerró recién en la Sesión 13, ver el
   listado de sesiones más abajo).
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
   documentos porque `Usuario` no tiene FK a `Proveedor` — cerrado en la
   Sesión 12. La consolidación automática de `bom_consolidado` →
   `requerimiento_anual_detalle` se cerró en la Sesión 13.
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
   el endpoint. **Cerrado en la Sesión 20** (jobs automáticos RN-11/RN-12
   vía APScheduler + endpoint de cierre mensual para RN-10).
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
   con diffs de columnas es una mejora futura, no bloqueante. **Cerrado
   en la revisión de deuda técnica de agosto 2026** (ver sección 10, tras
   la Sesión 21).
   Reportes: `GET /reportes/valorizacion-inventario`,
   `/comparativo-consumo` (BOM de Módulo 1A vs. comprado de Módulo 3 vs.
   recibido de Almacén vs. despachado de Módulo 4 — el que más tablas
   cruza) y `/alertas` (stock bajo, próximos a vencer, observaciones sin
   resolver). Límites documentados en el propio código: `/alertas` usaba
   `producto.stock_minimo_referencial` como único umbral —
   `almacen_producto_parametro` (override por almacén) no tenía modelo
   en ningún módulo (cerrado en la Sesión 17); "próximos a vencer" informa la
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
   (solo frontend), los selects de almacén muestran todos sin filtrar
   (el backend se cerró en la Sesión 15).
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
   fuera de alcance (solo frontend; el backend se cerró en la Sesión 15).
   ~~**Sesión 7 — Módulo Almacenes** (CRUD, Ubicaciones, Ingresos,
   Stock/Kardex, Movimientos, Inventarios físicos, Transferencias)~~ ✅
   implementado. Backend 100% completo desde antes — sesión puramente de
   frontend, la más grande hasta ahora (8 tabs, 17 rutas). `/almacenes`
   (Almacén: único CRUD "clásico" del módulo, reutiliza el patrón
   `mode: "create"|"edit"` de `ProveedorForm` de la Sesión 2;
   `responsable_id` es el único campo `responsable`/`almacenero` de todo
   el módulo que es client-supplied — todos los demás se derivan del
   usuario actual en el backend — resuelto con un select poblado desde
   `GET /usuarios`, primera vez que ese endpoint se consume en el
   frontend), `/almacenes/ubicaciones` (solo list+create, sin editar),
   `/almacenes/ingresos` (RN-04: el formulario de creación elige una
   **Inspección** como padre, no una guía — cada línea prellena
   `cantidad_ingresada` con `cantidad_conforme` de esa línea de
   inspección; igual que Recepción en la Sesión 6, no hay fetch extra
   para saber qué líneas ya tienen ingreso, el backend rechaza con 422 si
   una ya fue ingresada), `/almacenes/stock` y `/almacenes/kardex` (solo
   lectura, ambos denormalizados en el propio `Out` — sin lookups de
   cliente), `/almacenes/movimientos` (Ajuste/Merma/Devolución: **sin
   GET/lista/detalle en el backend**, tres formularios sueltos en una
   sola pantalla, cada uno limpia y muestra un link a Stock filtrado tras
   el éxito — no hay "detalle" al que navegar), `/almacenes/inventarios`
   (creación es solo una foto — `stock_sistema` es snapshot server-side,
   nunca input — y "Cerrar inventario" es quien genera los ajustes
   automáticos y mueve kardex, botón condicionado a `estado ===
   "EN_PROCESO"`), `/almacenes/transferencias` (RN-18: el stock sale del
   origen **al crear**, no al recibir; `TransferenciaRecepcionForm` es
   **todo-o-nada** — una fila por cada línea ya existente, sin
   agregar/quitar, se envían todas juntas en una sola llamada porque el
   backend rechaza recepciones parciales). No se construyó una pantalla
   de "bin card" — el schema `BinCardMovimientoOut` existe pero **ningún
   endpoint lo expone**, confirmado con grep sobre todo `app/api/v1/`
   antes de descartarlo, no solo por el reporte de exploración inicial.
   **Primer módulo con RN-20 real en escritura** (`verificar_acceso_almacen`,
   no solo `require_roles`) — verificado con un usuario `ALMACENERO`
   creado ad-hoc con acceso únicamente a un almacén de prueba, intentando
   una merma sobre otro almacén → 403 con el mensaje exacto de RN-20;
   las lecturas (GET) de este módulo, en cambio, **no** filtran por
   almacenes del usuario en ningún endpoint salvo `GET /almacenes` mismo
   (confirmado en el código, no solo asumido) — no se corrige, es un
   límite ya existente del backend, fuera de alcance de una sesión de
   frontend (cerrado en la Sesión 15). Verificado de punta a punta en el navegador contra una base
   SQLite descartable: almacén → ubicación → ingreso desde una inspección
   conforme (costo unitario correcto, tomado del contrato) → stock/kardex
   reflejando el ingreso → merma (-5) y devolución `DESDE_COCINA` (+3) →
   ajuste que dejaría stock negativo → 422 con el mensaje exacto del
   backend → transferencia entre 2 almacenes (stock del origen cae
   inmediatamente al crear, antes de cualquier recepción) → confirmar
   recepción con una cantidad menor a la enviada → `RECIBIDA_CON_DIFERENCIA`,
   costo unitario preservado del origen (no se re-promedia en destino) →
   inventario físico con una diferencia → cerrar → ajuste automático
   generado + movimiento `INVENTARIO_AJUSTE` en kardex con el saldo
   correcto → reintentar cerrar el mismo inventario → 422 (verificado por
   API, ya que el botón de cerrar desaparece correctamente en la UI una
   vez `CERRADO`, sin ruta de UI para provocar el duplicado).
   ~~**Sesión 8 — Módulo Cocina y consumo** (Solicitud de cocina, Nota
   de salida)~~ ✅ implementado. Backend 100% completo desde antes —
   sesión puramente de frontend, pequeña en contraste con la 7 (2
   sub-dominios, 2 routers). Primer módulo que activa
   `stock_comprometido`: `/cocina` (SolicitudCocina: list/nuevo/detalle
   — `almacen_id` nunca se manda, se deriva de `centro_consumo.
   almacen_id`; cada línea reserva la cantidad completa contra stock al
   crear, RN-07; `cantidad_teorica_bom` viene calculada server-side vía
   el puente `Producto.alimento_id` → `dosificacion_detalle`, el
   formulario solo la muestra de referencia, nunca la calcula ni la
   manda; máquina de estados `PENDIENTE → {ANULADA}` únicamente —
   `DESPACHADA` lo fija `NotaSalida.crear` como efecto secundario, nunca
   una transición directa), `/cocina/notas-salida` (NotaSalida:
   list/detalle de solo lectura — **sin pantalla "nueva"**, se crea
   siempre inline desde el detalle de su solicitud, mismo criterio que
   "Crear acta" en la Sesión 6 y "Autorizar excedente" en la Sesión 5).
   `CrearNotaSalidaForm` es **todo-o-nada** como
   `TransferenciaRecepcionForm` de la Sesión 7 — una fila fija por cada
   línea de la solicitud, sin agregar/quitar, porque el backend exige
   cobertura exacta (ni de más ni de menos) en una sola llamada.
   **Separación de roles real dentro de un mismo ítem de nav**: crear/
   anular solicitud → `ADMIN, COCINA`; crear nota de salida → `ADMIN,
   ALMACENERO` (el rol `COCINA` no puede despachar, confirmado en el
   propio router, no solo inferido del nombre). Prerrequisito real
   encontrado al planear: no existe un listado plano de `MenuDia` — el
   wrapper de "nueva solicitud" repite el patrón N+1 ya usado en
   sesiones previas (lista de menús quincenales + `GET .../{id}/dias`
   en paralelo, aplanados) para poblar el select de día de menú.
   Verificado de punta a punta en el navegador contra una base SQLite
   descartable con la cadena completa hasta dosificación calculada
   (mismo flujo de `test_cocina.py`: producto con `alimento_id` → ...→
   ingreso a almacén con stock real → receta VIGENTE → menú/día/plato →
   dosificación calculada): RN-20 con un usuario `COCINA` sin acceso al
   almacén (403) → solicitud dentro del disponible (201,
   `stock_comprometido` sube, `cantidad_teorica_bom` resuelta desde la
   dosificación) → RN-07 pidiendo más que el disponible restante (422
   con "RN-07" en el mensaje) → nota de salida con cobertura incompleta
   (422, verificado por API ya que el form siempre construye la
   cobertura completa por diseño) → nota de salida con despacho parcial
   (`cantidad_despachada` menor a la solicitada — `stock_fisico` baja
   solo lo despachado pero `stock_comprometido` libera el 100% de la
   reserva, `costo_unitario` y `variacion_pct` calculados correctamente,
   solicitud pasa a `DESPACHADA`) → no se puede anular una solicitud ya
   despachada (422) → tercera solicitud anulada sin despachar
   (`ANULADA`, reserva liberada a 0 sin ningún movimiento de kardex).
   ~~**Sesión 9 — Módulo Conformidad y pagos** (Informe de conformidad,
   Penalidad)~~ ✅ implementado. Cierra el último eslabón de
   trazabilidad de Compras: no decide nada nuevo sobre calidad — solo
   **lee** `acta_observacion.estado` (ya fijado por Recepción, Sesión 6)
   para cerrar la OC, generar el informe de pago y, si corresponde, la
   penalidad automática. Backend 100% completo desde antes — sesión
   puramente de frontend, con una particularidad: su punto de entrada
   natural no es una pantalla propia sino el **detalle de OC ya
   existente** (`compras/[id]/page.tsx`, Sesión 5), extendido con un
   bloque "Conformidad y pagos" (link al informe existente o
   `<GenerarInformeForm />` inline) en vez de duplicar el flujo.
   `/conformidad` (InformeConformidadPago: list + detalle +
   `<CambiarEstadoInformeForm />`), `/conformidad/penalidades` (Penalidad:
   list + `/nuevo` manual) — **sin `/conformidad/nuevo`**, mismo criterio
   que "Crear acta" (Sesión 6) y "Autorizar excedente" (Sesión 5): un
   informe solo se genera desde el detalle de una OC ya cerrada.
   `CambiarEstadoOC.tsx` (Sesión 5) no necesitó ningún cambio — ya POSTea
   `{estado:"CERRADO"}` genérico y hace `router.refresh()`, así que
   pinta sin tocar nada tanto `CERRADO` como `PENALIZADO` según decida el
   backend. **Máquina de estados del informe replicada en el cliente**
   (`ENVIADO→{RECIBIDO,DEVUELTO}`, `RECIBIDO→{EN_PROCESO_DE_PAGO,
   DEVUELTO}`, `EN_PROCESO_DE_PAGO→{PAGADO,DEVUELTO}`, `PAGADO`/
   `DEVUELTO` terminales) — a diferencia de `CambiarEstadoOC` (2 destinos
   fijos), acá cada estado ofrece hasta 2 destinos válidos distintos, así
   que `CambiarEstadoInformeForm.tsx` itera un `Record<string,string[]>`
   en vez de un `if` fijo. **Separación de roles real dentro de un mismo
   ítem de nav** (`nav.ts` agrupa todo bajo `ADMIN, LOGISTICA_CENTRAL,
   PAGOS`): cerrar OC + generar informe → `ADMIN, LOGISTICA_CENTRAL`
   (`PAGOS` no puede); cambiar estado del informe → `ADMIN, PAGOS`
   (`LOGISTICA_CENTRAL` no puede avanzar el pago pese a poder generar el
   informe). Verificado de punta a punta en el navegador contra una base
   SQLite descartable con dos OC completas hasta inspección (mismo flujo
   de `test_pagos.py`): OC-A (línea 100% conforme) → `Cerrar` → `CERRADO`
   sin penalidad → generar informe (`monto_conforme_total=110.00`,
   retenido/penalidad en 0) → avanzar
   `ENVIADO→RECIBIDO→EN_PROCESO_DE_PAGO→PAGADO` (en cada paso solo
   aparecían los botones de destino válidos) → `fecha_pago` se llena al
   llegar a `PAGADO`. OC-B (línea parcialmente observada, 15
   conforme/5 observada): cerrar con la línea `OBSERVADO` sin acta → 422
   ("tiene líneas OBSERVADO sin acta de observación resuelta") → crear
   acta (`ABIERTA`) → cerrar de nuevo → 422 (acta abierta sigue sin
   contar como resuelta) → agregar subsanación + registrar reinspección
   `NO_CONFORME` → acta pasa a `RECHAZADA` → cerrar OC-B → `PENALIZADO`
   (no `CERRADO`) → `Penalidad` automática visible en
   `/conformidad/penalidades` con `monto=27.50` (5 × S/5.50, origen
   "Automática (acta rechazada)") → generar informe de OC-B
   (`monto_conforme_total=82.50`, `monto_retenido_total=
   monto_penalidad_total=27.50`, ambos reflejando la línea rechazada) →
   penalidad manual en una tercera OC sin informe (OC-C, 201, origen
   "Manual") → penalidad manual en OC-A (ya con informe) → 422 ("ya se
   generó el informe de conformidad de esta OC"). `npx tsc --noEmit` +
   `npx eslint .` + `npx next build` limpios sobre el repo completo (49
   rutas generadas, incluidas las 4 nuevas de este módulo).
   ~~**Sesión 10 — Módulos "Reportes y auditoría" + "Administración"**~~
   ✅ implementado. Se originó de una revisión explícita de deuda técnica
   que encontró el hueco más visible del sistema: `frontend/lib/nav.ts`
   enlazaba `/reportes` y `/administracion` en el sidebar desde la Sesión
   1, pero ninguna de las dos carpetas existía bajo
   `frontend/app/(dashboard)/` — cualquier ADMIN que hiciera clic ahí caía
   en un 404. Primera sesión desde la 4 que vuelve a tocar backend: un
   agente de exploración confirmó que `reportes.py`/`auditoria.py` estaban
   completos pero **`usuarios.py` seguía igual que en la Sesión 1**
   (`GET` lista + `/me`, `POST` crear — nada más), con dos huecos reales
   que bloqueaban la pantalla de Administración — `UsuarioUpdate`
   (`schemas/usuario.py`) existía pero no estaba conectado a ningún
   endpoint, y no había forma de listar los roles disponibles para el
   select de "Nuevo usuario" (`rol_id` es obligatorio en `UsuarioCreate`).
   Se agregaron, mismo patrón que los huecos cerrados en Sesión 4:
   `GET /catalogos/roles` (`catalogos.py`, calca `listar_sedes`) y
   `PATCH /usuarios/{id}` (`usuarios.py` + nuevo
   `CRUDUsuario.update_con_almacenes` en `crud/usuario.py` — borra e
   inserta de nuevo las filas de `UsuarioAlmacenAcceso` si
   `almacen_ids is not None`, mismo patrón insert que
   `create_con_almacenes` con un `delete` previo). Primer test dedicado a
   usuarios (`backend/tests/test_usuarios.py`, no existía ninguno) cubre
   crear→login, `GET /catalogos/roles`, `PATCH` cambiando rol/estado/
   almacenes y su efecto real (`estado=INACTIVO` bloquea el login con 403
   — ya lo hacía `auth.py::login`, solo que nunca se había podido llegar
   ahí sin el `PATCH`), y 403 si quien llama no es `ADMIN`. **Límite de
   diseño aceptado conscientemente**: `UsuarioOut` no expone `sede_id`
   (solo el modelo y `UsuarioUpdate` lo tienen), así que el formulario de
   edición de usuario **no muestra el selector de sede** — mostrarlo
   habría precargado con `""` y el primer submit habría borrado en
   silencio la sede real del usuario sin que nadie la tocara. Se optó por
   ocultarlo en modo edición (igual que correo/contraseña, que tampoco se
   pueden editar) en vez de ampliar el alcance agregando `sede_id` a
   `UsuarioOut` — anotado aquí por si una sesión futura necesita permitir
   reasignar sede.
   Frontend: `/reportes` (4 tabs — Valorización, Comparativo de consumo,
   Alertas, Auditoría; los 3 endpoints de `reportes.py` solo filtran por
   `almacen_id` o `producto_id`+rango de fechas, **no** por contrato/
   proveedor/centro de consumo como promete la sección 3 del diseño — el
   frontend se construyó alrededor de lo que el backend realmente
   soporta; **`sede_id`/`proveedor_id`/`producto_id` cerrados más abajo**
   ["Deuda técnica: filtros de /reportes"], `centro_consumo_id` documentado
   ahí mismo como límite consciente; `AuditoriaLogOut` no trae nombre de
   usuario, solo
   `usuario_id`, así que la tabla muestra "Usuario #N" sin cruzar con
   `/usuarios` porque ese endpoint es `ADMIN`-only y `LOGISTICA_CENTRAL`
   —que también ve `/reportes`— recibiría 403 si el cruce se intentara
   forzado). `/administracion` (3 tabs — Usuarios, Productos, Catálogos):
   Usuarios reutiliza el patrón `mode:"create"|"edit"` de
   `ProveedorForm`/`AlmacenForm`, con checkboxes de almacenes que se
   ocultan si el rol elegido tiene `acceso_todos_almacenes=true`;
   Productos es CRUD completo (el backend ya lo tenía desde el
   prerrequisito de Sesión 2, nunca había tenido pantalla propia — solo se
   consumía como select en formularios de otros módulos); Catálogos es de
   solo lectura (categorías de alimento, unidades de medida, sedes,
   centros de consumo — los 4 endpoints de `catalogos.py` son GET-only,
   confirmado en el código). **"Parámetros del sistema"** (tercer punto de
   "09 Administración" en el diseño) **no se construyó en esta sesión —
   no existía ningún modelo ni tabla para eso en todo el backend** (grep
   sobre `models/`, `schemas/`, `api/`, sin resultados), documentado como
   límite explícito (a diferencia de `almacen_producto_parametro`,
   cerrado en la Sesión 17, este no tenía ni siquiera una tabla en el
   esquema — sería una sesión de alcance mayor, no solo mapear algo que
   ya existía); **cerrado en la Sesión 18** (tabla `parametro_sistema`
   nueva + pantalla `/administracion/parametros`).
   **Límite de alcance no resuelto
   aquí**: ni los 3 endpoints de `reportes.py` ni `GET /auditoria` tienen
   `require_roles(...)` en el backend — solo `get_current_user` — así que
   el gate `ADMIN`/`LOGISTICA_CENTRAL` de `/reportes` en `nav.ts` es
   puramente visual (oculta el ítem del menú, no protege la URL ni la
   API); mismo criterio que los huecos de RN-20 ya registrados en
   sesiones anteriores, fuera de alcance de esta sesión (cerrado en la
   Sesión 14). Verificado de
   punta a punta en el navegador contra una base SQLite descartable con
   el seed real (`python -m app.seed`, primera vez que una sesión de
   verificación usa el seed real en vez de reconstruir prerrequisitos a
   mano, porque esta sesión no depende de una cadena de negocio
   específica): los 4 tabs de `/reportes` cargan sin datos (esperado en
   una base recién sembrada) → crear usuario `ALMACENERO` con un almacén
   asignado → login con esas credenciales confirmado por API (200, JWT
   con `rol`/`almacenes` correctos) → editar ese usuario a `NUTRICION` +
   `INACTIVO` desde la UI → login vuelve a intentarse → 403 "Usuario
   inactivo" → `/reportes/auditoria?entidad=usuario` muestra las filas
   `CREAR`/`ACTUALIZAR` generadas por el evento global de auditoría
   (confirma que también audita la entidad `Usuario`, no solo los
   módulos de negocio) → crear producto → editarlo a `INACTIVO` → el
   filtro de estado de la lista lo excluye/incluye correctamente → las 4
   tablas de Catálogos se pintan. `npx tsc --noEmit` + `npx eslint .` +
   `npx next build` limpios sobre el repo completo (58 rutas generadas,
   incluidas las 8 nuevas de este módulo).
   ~~**Sesión 11 — Cerrar el hueco RN-20 en Compras y Recepción**~~ ✅
   implementado. Backend-only, sin cambios de frontend ni de modelos/
   schemas — cierra un hueco documentado explícitamente desde las
   Sesiones 5 y 6 ("mismo hueco de RN-20 que Compras... fuera de alcance,
   solo frontend"). Cinco routers nunca validaban RN-20 en sus escrituras:
   `pedidos_semanales.py`, `ordenes_compra.py`, `guias_remision.py`,
   `inspecciones.py`, `actas_observacion.py`. Se aplicó el mismo patrón ya
   probado en Almacén/Cocina (`deps.py::verificar_acceso_almacen`) a cada
   endpoint POST/PATCH de esos 5 archivos, resolviendo `almacen_id` según
   su origen real: campo directo del body
   (`PedidoSemanalCreate.almacen_id`, `GuiaRemisionCreate.
   almacen_destino_id`), o derivado de una entidad relacionada vía FK
   cuando el body no lo trae (`InspeccionCreate.guia_remision_id` →
   `GuiaRemision.almacen_destino_id`; `guia_remision_id`/
   `orden_compra_detalle_id`/`inspeccion_detalle_id`/
   `acta_observacion_id`/`subsanacion_id` como path params → un `db.get`
   en cadena hasta llegar al almacén). **Deliberadamente NO se tocó
   ningún `GET`/lista** de estos 5 archivos — mismo criterio ya
   documentado en la Sesión 7 (Almacén tampoco filtra lecturas por
   almacenes del usuario), así que esto es consistente con el resto del
   backend, no un vacío nuevo.
   `OrdenCompra` es el único caso multialmacén real (RN-15,
   `OrdenCompraDistribucion` 1..N por línea) — sin precedente de código
   para decidir "ALL vs ANY", se resolvió **ALL** (el usuario necesita
   acceso a *todos* los almacenes que la escritura toca en una sola
   llamada atómica), verificado con un test que prueba explícitamente que
   una distribución mitad-autorizada-mitad-no sigue bloqueada. Caso
   particular encontrado al implementar `actas_observacion.py`: la cadena
   de FKs para llegar al almacén cambia en cada uno de los 3 endpoints de
   escritura (`inspeccion_detalle_id` → `acta_observacion_id` →
   `subsanacion_id`, cada uno un salto más), así que se armaron 3 helpers
   privados que se componen (`_almacen_id_de_inspeccion_detalle` →
   `_almacen_id_de_acta` → `_almacen_id_de_subsanacion`) en vez de repetir
   la cadena completa en cada endpoint;
   `InspeccionDetalle.guia_remision_detalle` es `lazy="joined"` así que el
   primer salto no cuesta una query aparte, pero
   `GuiaRemisionDetalle.guia_remision` no lo es, así que sí hace falta un
   `db.get(GuiaRemision, ...)` adicional ahí. **Límite consciente**: si el
   `db.get`/`select` de la entidad no encuentra nada (ID inexistente), el
   endpoint no levanta su propio 404 — se deja pasar sin llamar a
   `verificar_acceso_almacen` para que el CRUD ya existente levante el
   `ValueError` de "no encontrado" que ya tenía, sin duplicar esa
   validación en dos capas.
   `test_compras.py`/`test_inspeccion.py` solo probaban con tokens
   `ADMIN` (`acceso_todos_almacenes=True`) — se agregó `_headers_rol(rol,
   almacenes)` (mismo patrón que `test_almacen.py`/`test_cocina.py`) y un
   `test_rn20_alcance_por_almacen` en cada archivo cubriendo los 9
   endpoints tocados, cada uno con caso bloqueado (403 con el mensaje
   exacto de RN-20) y caso permitido. **Nota real encontrada al verificar
   manualmente vía API contra un seed real**: `ordenes_compra.py` solo
   admite escribir a `ADMIN`/`LOGISTICA_CENTRAL`, y ambos roles tienen
   `acceso_todos_almacenes=True` siempre (confirmado vía
   `GET /catalogos/roles` contra el seed real) — así que ese chequeo
   específico es defensivo/a futuro (protege si algún día se agrega un
   rol con acceso restringido a `ROLES_EDICION` de OC), no alcanzable hoy
   por un login legítimo; los tests de pytest sí lo ejercitan porque
   construyen el JWT directo con `create_access_token(rol=
   "LOGISTICA_CENTRAL", acceso_todos_almacenes=False)`, sin pasar por
   login. Los otros 4 archivos sí involucran roles reales con
   `acceso_todos_almacenes=False` (`NUTRICION`, `PROVEEDOR`, `INSPECTOR`)
   y se verificaron además con logins reales contra el seed:
   `pedidos-semanales` y `guias-remision` devolvieron el 403 exacto de
   RN-20 al apuntar a un almacén no asignado, y pasaron la validación
   (fallando después por otro motivo esperado, sin datos de prueba
   completos) al apuntar al almacén sí asignado. `pytest -q` completo:
   18 tests en verde (suite previa intacta + los 2 nuevos).
   ~~**Sesión 12 — Alcance de PROVEEDOR (Usuario → Proveedor)**~~ ✅
   implementado. Cierra un hueco de confidencialidad documentado desde la
   Sesión 2: `Usuario` no tenía FK a `Proveedor`, así que cualquier
   usuario con rol `PROVEEDOR` veía y podía tocar los contratos, OCs,
   guías y el directorio completo de proveedores del sistema — precios
   pactados y condiciones de la competencia incluidos, no solo los
   propios. Backend + frontend, con un cambio de esquema real (primero
   desde la Sesión 1 que agrega una columna a una tabla ya existente).
   **Esquema**: `usuario.proveedor_id INT NULL` + FK a `proveedor`,
   agregada directo en `db/init/01_schema.sql` (instalaciones nuevas) y
   replicada en `db/patches_historicos/11_parche_usuario_proveedor.sql`
   (mismo patrón que `09_parche_password_usuario.sql`) para bases ya
   corriendo. Alembic sigue en su baseline no-op (`0001_baseline.py`) —
   se confirmó que nunca se usó para un cambio real, así que este parche
   sigue el precedente real del proyecto (SQL directo) en vez de
   introducir la primera migración Alembic real, que habría sido un
   cambio de proceso más grande que el propio fix.
   **JWT/identidad**: `create_access_token`/`CurrentUser` ganan
   `proveedor_id: int | None` (mismo mecanismo que `almacenes`/
   `acceso_todos_almacenes` para RN-20) — `_emitir_tokens` en `auth.py`
   lo lee de `usuario.proveedor_id` en login y refresh. Nuevo
   `CurrentUser.tiene_acceso_proveedor`/`deps.py::verificar_acceso_proveedor`,
   mismo mensaje/status que su equivalente de almacén, pero con una
   diferencia deliberada: **no restringe a nadie salvo al propio rol
   `PROVEEDOR`** (ADMIN/LOGISTICA_CENTRAL nunca se bloquean, a diferencia
   de `tiene_acceso_almacen` que depende de `acceso_todos_almacenes`).
   **Alcance aplicado** (patrón: listas fuerzan el filtro según el rol,
   detalle/escritura llaman `verificar_acceso_proveedor` tras resolver el
   `proveedor_id` real): `proveedores.py` (nuevo filtro `proveedor_id` en
   `crud/proveedor.py::list_filtrado`, antes solo `estado`/`buscar`),
   `contratos.py` (ya tenía el filtro, solo faltaba forzarlo),
   `ordenes_compra.py` (nuevo filtro en `crud/orden_compra.py::list_filtrado`
   vía `.join(Contrato)`, ya que `OrdenCompra` no tiene `proveedor_id`
   directo — solo llega vía `contrato_id → Contrato.proveedor_id`),
   `guias_remision.py` (list + detalle + **creación**, esta última cierra
   un hueco de impersonación real: antes un `PROVEEDOR` autenticado podía
   mandar el `proveedor_id` de otro proveedor en el body al crear una
   guía). `actas_observacion.py::crear_subsanacion` reutiliza los mismos
   helpers de la Sesión 11 (`_almacen_id_de_inspeccion_detalle` etc.),
   generalizados para devolver el objeto `GuiaRemision` completo en vez
   de solo el almacén, evitando una segunda cadena de fetches paralela
   para `.proveedor_id`. **Fuera de alcance, a propósito**:
   `inspecciones.py` y el resto de `actas_observacion.py` (`PROVEEDOR`
   nunca escribe ahí) y `pedidos_semanales.py` (sin vínculo directo a
   proveedor en el modelo, cerrado en la Sesión 16) — ampliar más allá
   del hueco descrito ("ve todas las OCs/contratos/guías") quedó fuera
   de esta sesión.
   Frontend: `UsuarioForm.tsx` (Sesión 10) gana un select "Proveedor"
   condicional (`rolSeleccionado?.nombre === "PROVEEDOR"`, mismo criterio
   que el ocultamiento de almacenes cuando `acceso_todos_almacenes`),
   visible tanto en alta como en edición (a diferencia de `sede_id`, que
   solo se define al crear — aquí si tiene sentido poder reasignar el
   proveedor de un usuario ya existente). Regenerado el cliente orval
   para traer `proveedor_id` en `UsuarioCreate`/`UsuarioUpdate`/
   `UsuarioOut`. **Tests**: `test_usuarios.py` (crear/actualizar
   `proveedor_id`), `test_contratos.py`/`test_compras.py`/
   `test_inspeccion.py` con **dos proveedores independientes** cada uno
   (se parametrizó `_preparar_contrato_con_producto` con overrides de
   código/RUC/número de contrato para poder llamarla dos veces en el
   mismo test sin chocar con las constraints UNIQUE) — lista filtrada sin
   que el cliente tenga que pedirlo, detalle cruzado bloqueado (403), e
   impersonación de guía bloqueada. Efecto colateral esperado: los tests
   RN-20 de la Sesión 11 que usaban tokens `PROVEEDOR` sin `proveedor_id`
   dejaron de pasar (ahora se bloquean también por proveedor, no solo por
   almacén) — se corrigió pasando el mismo `proveedor_id` en ambos tokens
   de cada test para aislar la dimensión que cada uno prueba. Verificado
   además con un login real de punta a punta contra un seed real: usuario
   `PROVEEDOR` creado desde `/administracion/nuevo` con su proveedor
   asignado → login real → `GET /proveedores` devuelve solo el propio →
   `GET /proveedores/{id}` de un competidor → 403 con el mensaje exacto.
   `pytest -q` completo: 21/22 en verde (el único rojo es
   `test_reportes.py::test_reportes_completo`, una fragilidad ya existente
   y ajena a esta sesión — compara fechas con `date.today()` local contra
   un timestamp SQLite en UTC, y el entorno estaba pasada la medianoche
   UTC durante la verificación; queda anotado como tarea aparte, no se
   tocó en esta sesión). `npx tsc --noEmit` + `npx eslint .` +
   `npx next build` limpios sobre el repo completo (mismas 58 rutas, sin
   rutas nuevas — solo cambios de formulario).
   ~~**Sesión 13 — Consolidación automática BOM → Requerimiento anual**~~ ✅
   implementado. Cierra la deuda documentada desde la Sesión 2: hasta ahora
   `RequerimientoAnual` era 100% entrada manual pese a que el Módulo 1A ya
   calcula, por día de menú, la explosión de materiales real (RN-24,
   `DosificacionDetalle`). `bom_consolidado` existía en `01_schema.sql`
   desde el bootstrapping inicial pero nunca tuvo modelo ORM (confirmado
   con grep sobre todo `backend/` antes de empezar) — se mapeó en
   `models/dosificacion.py::BomConsolidado` (mismo archivo que
   `DosificacionDetalle`; `bom_consolidado_id` es `BIGINT AUTO_INCREMENT`,
   así que usa `BigIntPK` de `db/base.py`, gotcha ya conocido de sección
   7.4). Puente real que no existía en ningún código previo:
   `DosificacionDetalle.alimento_id` (catálogo nutricional) se une a
   `Producto.alimento_id` (nullable, no único a nivel de esquema — se
   asume 1:1 en la práctica, límite documentado) para llegar a
   `Producto.producto_id`, que es lo que `RequerimientoAnualDetalle`
   realmente requiere.
   Backend: `crud/bom_consolidado.py::ServicioBomConsolidado.
   generar_y_consolidar` agrega `dosificacion_detalle` de **todos** los
   días de menú de una `RacionAnual` (join `MenuDia`→`MenuQuincenal`
   filtrado por `racion_anual_id`, agrupado por almacén+producto), calcula
   `stock_disponible_referencia` (foto de `StockAlmacenProducto.
   stock_fisico`) y `saldo_contractual_referencia` (suma de
   `ProductoContratado.saldo_fisico` de contratos `VIGENTE` para ese
   producto, RN-19 GLOBAL), inserta filas `BomConsolidado` (idempotente:
   borra+recrea las del mismo periodo+almacén+producto, mismo patrón que
   `ServicioDosificacion.calcular_dia`) y reutiliza
   `requerimiento_repo.crear_con_detalle` tal cual para crear el
   `RequerimientoAnual`(BORRADOR) sumando cantidades entre almacenes.
   Dos endpoints nuevos en `api/v1/planificacion.py`: `POST .../raciones-
   anuales/{id}/consolidar-requerimiento` (roles `ADMIN, NUTRICION`,
   reutiliza `ROLES_EDICION` ya definido) y `GET .../bom-consolidado`
   (cualquier usuario autenticado). Límites explícitos de esta versión
   (documentados también en el docstring del servicio, mismo criterio que
   otros MVP de sesiones anteriores): `tipo_periodo` fijo en `"ANIO"`
   (1 ene/31 dic del año de la ración anual — la tabla soporta SEMANA/
   QUINCENA/MES pero no se expone esa granularidad); `estado_suficiencia`
   solo distingue `SUFICIENTE`/`ALERTA_CONTRATO` (comparando cantidad
   requerida vs. saldo contractual) — `ALERTA_STOCK` no se genera porque
   no hay una regla clara en el diseño para combinar stock físico con
   saldo contractual sin inventar una fórmula arbitraria; un solo
   `RequerimientoAnual` por `racion_anual_id` (422 si ya existe uno,
   cualquier estado — evita la complejidad de un flujo de "nueva versión"
   que no existía para reutilizar); `bom_consolidado` no tiene columna
   `racion_anual_id` en el esquema, así que la lectura se scope por año
   calendario, no por ración exacta (si dos raciones anuales del mismo año
   consolidan el mismo almacén+producto, la segunda reemplaza la foto de
   la primera — límite de esquema, no de la lógica).
   Frontend: `planificacion/[id]/page.tsx` (detalle de Ración anual,
   Sesión 4) gana un bloque "Requerimiento anual (BOM)" con el mismo
   patrón "verificar existencia antes de decidir qué mostrar" que
   "Conformidad y pagos" en `compras/[id]/page.tsx` (Sesión 9): si ya
   existe un requerimiento para esa ración (`GET /requerimientos-anuales?
   racion_anual_id=X`, filtro que ya existía desde el Módulo 2) muestra un
   link a su detalle; si no y el usuario puede editar, muestra
   `<ConsolidarRequerimientoForm>` (nuevo, mismo estilo sin campos que
   `GenerarInformeForm`/`AutorizarExcedenteForm`) que redirige al
   requerimiento creado. Verificado de punta a punta en el navegador
   contra una base SQLite descartable con el seed real: alimento → receta
   VIGENTE → producto con `alimento_id` puente → ración anual → menú
   quincenal → día → plato → dosificación calculada (18 unidades) →
   consolidar (201, requerimiento BORRADOR con la línea correcta) →
   `GET .../bom-consolidado` (`estado_suficiencia="ALERTA_CONTRATO"`, sin
   contrato todavía) → repetir consolidación → 422 ("Ya existe...") →
   detalle de la ración muestra el link en vez del botón tras refrescar.
   Test nuevo en `test_planificacion.py::test_consolidar_requerimiento_
   desde_bom` cubre además el caso `SUFICIENTE` (contrato+producto_
   contratado con saldo suficiente, segunda ración anual consolidada) y el
   422 de precondición (ración sin dosificación calculada). `pytest -q`
   completo: 23/24 en verde (el único rojo sigue siendo el mismo flake
   preexistente y ajeno de `test_reportes.py::test_reportes_completo`,
   ya documentado en la Sesión 12). `npx tsc --noEmit` + `npx eslint .`
   limpios sobre el repo completo.
   ~~**Sesión 14 — Autorización de roles en Reportes/Auditoría**~~ ✅
   implementado. Backend-only, sin cambios de frontend/schema/modelo —
   cierra un límite documentado explícitamente desde la Sesión 10: los 3
   endpoints de `reportes.py` y `GET /auditoria` solo tenían
   `get_current_user`, sin `require_roles(...)`, así que cualquier rol
   autenticado (`ALMACENERO`, `COCINA`, `PROVEEDOR`, etc.) podía llamarlos
   directo por API pese a que `frontend/lib/nav.ts` oculta el ítem
   "Reportes y auditoría" del sidebar salvo para `ADMIN`/
   `LOGISTICA_CENTRAL` — ese gate era puramente visual. Fix: nueva
   constante `ROLES_LECTURA = ("ADMIN", "LOGISTICA_CENTRAL")` (mismos
   roles que `nav.ts`) en ambos archivos, reemplazando
   `Depends(get_current_user)` por
   `Depends(require_roles(*ROLES_LECTURA))` en los 4 endpoints
   (`reporte_valorizacion_inventario`, `reporte_comparativo_consumo`,
   `reporte_alertas`, `listar_auditoria`). A diferencia de catálogos de
   uso transversal legítimo entre roles (ej. `GET /productos`, que sí
   necesita `require_roles` solo en escritura), aquí se protegió también
   la **lectura** porque estos son reportes agregados de todo el sistema
   sin ningún caso de uso legítimo para roles operativos como
   `ALMACENERO`/`COCINA`. Tests nuevos:
   `test_reportes.py::test_reportes_requiere_rol_autorizado` (token
   `COCINA` sin `require_roles` → 403 en los 3 endpoints; token
   `LOGISTICA_CENTRAL` → 200/404 según el caso) y
   `test_auditoria.py::test_auditoria_requiere_rol_autorizado` (mismo
   patrón, `ALMACENERO` bloqueado, `LOGISTICA_CENTRAL` permitido) — ambos
   con un nuevo helper `_headers_rol(rol)` local a cada archivo (mismo
   patrón `create_access_token` ya usado en `test_cocina.py`/
   `test_almacen.py`). Los tests preexistentes de ambos archivos solo
   usaban `_headers_admin()`, así que no se rompió nada. Verificado además
   con un login real contra un seed real: usuario `ALMACENERO` creado
   desde `/administracion` → login real → `GET /reportes/alertas` y
   `GET /auditoria` → 403 exacto ("El rol 'ALMACENERO' no tiene permiso
   para esta operación"); con el token del admin, ambos → 200.
   `pytest -q` completo: 24/25 en verde (el único rojo sigue siendo el
   mismo flake preexistente de `test_reportes.py::test_reportes_completo`,
   ajeno a esta sesión). `npx tsc --noEmit` + `npx eslint .` limpios (sin
   cambios de frontend en esta sesión).
   ~~**Sesión 15 — RN-20 en lecturas (GET): Almacén, Compras y
   Recepción**~~ ✅ implementado. Backend-only. RN-20 se cerró para
   **escrituras** en la Sesión 11 (`verificar_acceso_almacen`) en 5
   routers, pero cada sesión posterior que tocó esos módulos documentó
   explícitamente que las **lecturas** seguían sin filtrar por almacén —
   un `ALMACENERO`/`INSPECTOR` con acceso a un solo almacén podía listar y
   ver el detalle de documentos de *cualquier* almacén, solo no escribir
   sobre ellos. Se auditaron los 22 endpoints `GET` de 12 archivos
   (`almacenes.py`, `ubicaciones.py`, `ingresos_almacen.py`, `stock.py`,
   `inventarios_fisicos.py`, `transferencias_almacen.py`,
   `pedidos_semanales.py`, `guias_remision.py`, `inspecciones.py`,
   `actas_observacion.py`, `ordenes_compra.py`) — ninguno filtraba por
   almacén salvo `GET /almacenes`, que además tenía un bug real: filtraba
   en Python **después** de paginar en SQL, rompiendo `total`/paginación
   para roles restringidos (corregido de paso, mismo archivo que ya había
   que tocar).
   Patrón nuevo en `deps.py::resolver_almacenes_visibles(current,
   almacen_id)`: para roles sin `acceso_todos_almacenes`, retorna la lista
   de almacenes a la que restringir un listado vía `IN` (o `[]` si el
   cliente pidió un `almacen_id` fuera de su alcance — `.in_([])` compila
   a una condición siempre falsa en SQLAlchemy, cero filas sin necesidad
   de un 403 que filtre si ese almacén existe). Cada `list_filtrado`/
   `list_stock`/`list_kardex` afectado ganó un parámetro `almacen_ids:
   list[int] | None` aplicado como `.in_(...)`, coexistiendo con el
   filtro `almacen_id` de igualdad ya existente — para roles con acceso
   total el comportamiento es idéntico a antes (cero regresión, todos los
   tests previos usan `_headers_admin()`). Detalle: mismo
   `verificar_acceso_almacen` ya usado en escritura, ahora también tras el
   fetch de lectura.
   Tres casos con join/agregación genuina, no solo columna directa:
   `inspecciones.py` (`Inspeccion.guia_remision` es `lazy="joined"`, así
   que `inspeccion.guia_remision.almacen_destino_id` no cuesta query
   extra); `actas_observacion.py` (cadena de 3 saltos `ActaObservacion` →
   `InspeccionDetalle` → `GuiaRemisionDetalle` → `GuiaRemision`, la más
   profunda — el detalle reutiliza el helper `_guia_de_acta` ya creado en
   la Sesión 11 en vez de repetir la cadena); `ordenes_compra.py`
   (`EXISTS` a través de `OrdenCompraDetalle`→`OrdenCompraDistribucion` en
   vez de un `JOIN` simple, para no duplicar filas de una OC distribuida a
   varios almacenes y no romper la paginación).
   **Dos entidades multialmacén con política ANY, no ALL**:
   `OrdenCompra` (vía `detalle[].distribucion[]`) y `TransferenciaAlmacen`
   (origen/destino) son visibles si el usuario tiene acceso a **al menos
   uno** de los almacenes involucrados — deliberadamente distinto del
   **ALL** decidido en la Sesión 11 para crear/cambiar-estado de una OC
   (escribir sobre todos los almacenes de una vez es más riesgoso que
   verlos). `TransferenciaAlmacen` es además la única con un filtro `OR`
   real (`or_(origen.in_(ids), destino.in_(ids))`) en vez del `IN` simple
   del resto.
   Tests nuevos (mismo patrón `_headers_rol`/`_headers_almacenero` ya
   establecido en la Sesión 11 — dos almacenes, un documento en cada uno,
   token restringido al almacén 1, verificar lista filtrada + detalle
   ajeno en 403 + regresión con ADMIN): `test_compras.py::
   test_rn20_lecturas_ordenes_compra_pedidos_guias` (incluye el caso ANY
   con una OC distribuida a ambos almacenes), `test_inspeccion.py::
   test_rn20_lecturas_inspecciones_actas` (con un nuevo helper
   `_crear_guia_en_almacen`, variante de `_crear_guia_completa` que
   permite fijar el almacén — ese ya existente siempre usa el 1),
   `test_almacen.py::test_rn20_lecturas_almacen` (ubicaciones, ingresos,
   stock, kardex, inventarios físicos, y el caso OR de transferencias).
   `pytest -q` completo: 27/28 en verde (mismo flake preexistente de
   `test_reportes.py::test_reportes_completo`, ajeno a esta sesión).
   Verificado además con un login real contra un seed real: usuario
   `ALMACENERO` con acceso a un solo almacén (de 4 reales) → `GET
   /almacenes` devuelve solo el suyo con `total` correcto (confirma el fix
   del bug de paginación) → `GET /ubicaciones` solo la propia → `GET
   /almacenes/{id}` de otro almacén → 403. `npx tsc --noEmit` + `npx
   eslint .` limpios (sin cambios de frontend en esta sesión).
   ~~**Sesión 16 — Alcance de PROVEEDOR en Pedidos semanales**~~ ✅
   implementado. Backend-only, el más pequeño de esta racha de sesiones
   de deuda técnica. Cierra un límite documentado explícitamente desde la
   Sesión 12: `pedidos_semanales.py` quedó fuera de esa sesión porque
   `PedidoSemanal` no tiene columna `proveedor_id` directa — cualquier
   `PROVEEDOR` autenticado podía listar/ver el detalle de **todos** los
   pedidos semanales del sistema, pese a que `Contrato`/`OrdenCompra`/
   `GuiaRemision` ya estaban acotados. El camino real es `PedidoSemanal.
   orden_compra_id` → `OrdenCompra.contrato_id` → `Contrato.proveedor_id`;
   como `PROVEEDOR` nunca está en `ROLES_EDICION` de este router (el
   diseño dice "[Logística/Nutrición] genera Pedido Semanal"), el hueco
   era puramente de lectura, no de escritura. Mismo patrón "lista fuerza
   el filtro, detalle verifica" de la Sesión 12:
   `crud/pedido_semanal.py::list_filtrado` gana `proveedor_id` (mismo
   `.join(OrdenCompra).join(Contrato)` ya usado en `orden_compra_repo.
   list_filtrado`); el router fuerza `proveedor_filtro = current.
   proveedor_id if current.rol == "PROVEEDOR" else None`; el detalle
   agrega `verificar_acceso_proveedor(current, pedido.orden_compra.
   contrato.proveedor_id)` junto al `verificar_acceso_almacen` que ya
   tenía. Confirmado que `pedido.orden_compra.contrato.proveedor_id` no
   dispara I/O extra tras `get_con_relaciones`: `PedidoSemanal.orden_compra`
   y `OrdenCompra.contrato` están declarados `lazy="joined"` a nivel de
   mapper, y SQLAlchemy aplica esa estrategia de forma transitiva para
   cualquier carga de esas clases (mismo razonamiento ya usado en la
   Sesión 11 para las cadenas de `actas_observacion.py`) — los 5 tests
   nuevos pasaron a la primera sin necesitar añadir ningún `.options()`.
   Test nuevo: `test_compras.py::test_rn_alcance_proveedor_pedidos_semanales`
   (dos proveedores independientes, cada uno con su propia OC + pedido
   semanal — mismo patrón que `test_rn_alcance_proveedor`). `pytest -q`
   completo: 29/29 en verde (el flake de `test_reportes.py` no se disparó
   esta vez — depende de la hora UTC exacta, sigue siendo el mismo
   problema preexistente y ajeno, no una señal de que se haya corregido).
   Verificado con un login real contra un seed real: dos cadenas
   proveedor→contrato→OC→pedido semanal completas por API, usuario
   `PROVEEDOR` real vinculado al proveedor A **y con un almacén asignado**
   (sin almacén asignado, RN-20 ya bloquea todo antes de llegar al chequeo
   de proveedor — se encontró este matiz recién al verificar manualmente:
   la primera prueba con un usuario `PROVEEDOR` sin `almacen_ids` dio
   `total: 0` por RN-20, no por el fix de esta sesión, hubo que asignarle
   un almacén con `PATCH /usuarios/{id}` para aislar la dimensión que
   realmente se estaba probando) → `GET /pedidos-semanales` devuelve solo
   el propio → detalle propio → 200 → detalle del proveedor B (mismo
   almacén) → 403 exacto ("No tienes autorización para operar sobre los
   documentos de este proveedor"). `npx tsc --noEmit` + `npx eslint .`
   limpios (sin cambios de frontend en esta sesión).
   ~~**Sesión 17 — Parámetro de stock mínimo por almacén**~~ ✅
   implementado. Cierra el límite documentado desde la Sesión 10:
   `/reportes/alertas` usaba un único umbral global
   (`Producto.stock_minimo_referencial`) para "stock bajo", sin poder
   ajustarlo por almacén. `almacen_producto_parametro` **ya existía en
   `01_schema.sql`** (PK compuesta `almacen_id`+`producto_id`,
   `stock_minimo`) desde el bootstrapping inicial pero nunca tuvo modelo
   ORM — mismo patrón que `bom_consolidado` en la Sesión 13, sin cambios
   de esquema/parche necesarios.
   Backend: `models/inventario.py::AlmacenProductoParametro` (mismo
   archivo/patrón que `StockAlmacenProducto` — PK compuesta, relaciones
   `almacen`/`producto` `lazy="joined"`); `crud/parametro_stock.py`
   (nuevo, funciones sueltas en vez de `CRUDBase` porque la PK compuesta
   no encaja con `CRUDBase.get(db, pk)` de un solo valor —
   `list_filtrado`, `upsert` con `db.get(Modelo, (almacen_id,
   producto_id))` para decidir crear vs. actualizar, `eliminar`);
   `api/v1/parametros_stock.py` (nuevo router `/parametros-stock`: `GET`
   con el mismo alcance de lectura RN-20 de la Sesión 15, `PUT`/`DELETE`
   con `require_roles("ADMIN", "LOGISTICA_CENTRAL")` — mismos roles que
   `PATCH /productos/{id}`, dueño del umbral global — + `verificar_acceso_
   almacen` defensivo, igual que el caso ya documentado en
   `ordenes_compra.py` en la Sesión 11, porque esos dos roles siempre
   tienen `acceso_todos_almacenes=True`). `crud/reportes.py::_stock_bajo`
   se reescribe con un `outerjoin` a la tabla nueva y
   `func.coalesce(override, global)` como umbral efectivo — el campo de
   salida `StockBajoOut.stock_minimo_referencial` **no cambia de
   nombre** (evita tocar schema/frontend ya existentes) pero ahora
   refleja ese umbral efectivo, documentado con un comentario en el
   propio código. Tabla con PK compuesta → no se audita (mismo criterio
   ya establecido para `stock_almacen_producto` desde la Sesión 7, nada
   que tocar en `core/audit.py`).
   Frontend: nueva pestaña "Parámetros de stock" en `/almacenes`
   (`ModuleTabs.tsx`) → `/almacenes/parametros` (lista + `SelectFilter`
   por almacén, mismo patrón que `ubicaciones/page.tsx`) con
   `<ParametroStockForm>` (upsert inline, solo ADMIN/LOGISTICA_CENTRAL) y
   `<EliminarParametroButton>` por fila.
   **Bug real encontrado y corregido durante la verificación en el
   navegador**: `app/api/backend/[...path]/route.ts` (el proxy compartido
   por todos los Client Components desde la Sesión 1) construía
   `new NextResponse(responseBody, {status, headers})` pasando siempre un
   `ArrayBuffer` como body — la spec de Fetch/Response prohíbe un body no
   nulo en respuestas 204/205/304, y el runtime de Next.js lo revienta en
   tiempo de ejecución (500) al intentarlo. Nunca se había manifestado
   porque `DELETE /parametros-stock/{almacen_id}/{producto_id}` es el
   **primer endpoint de todo el backend que responde 204** — confirmado
   con `grep -rn "204" app/api/v1/*.py` antes de escribirlo así. El
   borrado en sí funcionaba de punta a punta en el backend (confirmado
   por API directa que la fila desaparecía de la base pese al 500 que
   veía el navegador); el bug estaba solo en la capa de relay hacia el
   cliente. Fix: `responseBody` es `null` cuando `backendResponse.status`
   es 204/205/304, antes de construir el `NextResponse`. No se optó por
   evitar el problema devolviendo 200 en el endpoint nuevo — se corrigió
   la causa raíz en el proxy compartido, porque cualquier futuro endpoint
   204 habría pisado el mismo bug.
   Test nuevo: `test_almacen.py::test_parametro_stock_por_almacen`
   (mismo stock físico en dos almacenes, uno sin override usa el umbral
   global y aparece en `stock_bajo`, el otro con override no aparece;
   `DELETE` revierte al umbral global; RN-20 en escritura con
   `_headers_almacenero`). `pytest -q` completo: 30/30 en verde. Verificado
   de punta a punta en el navegador contra una base SQLite descartable:
   crear parámetro (`PUT`, 200) → tabla lo muestra → eliminar (`DELETE`,
   204 tras el fix del proxy, confirmado también con un `GET` directo por
   API que la fila ya no existe) → `/reportes/alertas` sigue renderizando
   sin errores. `npx tsc --noEmit` + `npx eslint .` + `npx next build`
   limpios (59 rutas, incluida la nueva).
   ~~**Sesión 18 — Parámetros del sistema (Administración)**~~ ✅
   implementado. Cierra el último punto documentado como "no construido"
   de "09 Administración" (sección 10, Sesión 10) — a diferencia de
   `almacen_producto_parametro` (Sesión 17), esta tabla **no existía en
   absoluto** en `01_schema.sql`, así que fue la primera sesión desde la
   12 en agregar una tabla nueva de cero (con su parche histórico) en vez
   de mapear algo que ya existía.
   **Alcance investigado antes de planear**: el diseño original solo
   menciona "Parámetros del sistema" como bullet, sin ninguna
   especificación — se buscaron candidatos reales de umbrales hardcodeados
   (`grep` sobre `app/`) y se encontraron tres: `Contrato.alerta_vigencia`
   (30 días), `ProductoContratado.alerta_saldo` (15%) y `dias_vencimiento`
   de `/reportes/alertas` (30, Sesión 10). Los dos primeros son
   `@property` de SQLAlchemy puros, serializados por Pydantic vía
   `from_attributes=True` automático sin `db` en scope — conectarlos
   habría exigido convertir esa serialización automática en
   `from_model(obj, umbral)` explícito en ~4-6 endpoints de
   `contratos.py`, un refactor aparte con su propio riesgo. Se decidió,
   de forma consciente y documentada (no silenciosa), conectar solo
   `dias_vencimiento` (un query param FastAPI plano, sin ese problema) y
   dejar los otros dos como límite explícito — mismo criterio que
   `ActaObservacion.plazo_vencido` (RN-11), idéntico patrón de `@property`.
   **`alerta_vigencia`/`alerta_saldo` cerrados en la Sesión 19;
   `plazo_vencido` se investigó ahí mismo y se descartó — no comparte el
   mismo patrón, no hay número hardcodeado que extraer (ver esa sesión).**
   **Esquema**: tabla nueva `parametro_sistema` (`clave` VARCHAR(60) PK,
   `valor` VARCHAR(255), `descripcion` opcional, `actualizado_en`
   DATETIME con `onupdate=func.now()` solo a nivel ORM — mismo patrón que
   `stock_almacen_producto.actualizado_en`, confirmado antes de escribirlo
   leyendo esa columna en `01_schema.sql` — y `actualizado_por_id` FK
   opcional a `usuario`), agregada a `db/init/01_schema.sql` +
   `db/patches_historicos/12_parche_parametro_sistema.sql` (mismo patrón
   que `11_parche_usuario_proveedor.sql`, sigue el precedente de no usar
   Alembic para esto, ya justificado en la Sesión 12).
   **Backend**: `models/sistema.py` (nuevo, un solo modelo — mismo
   criterio de `models/auditoria.py` para un concern transversal),
   `schemas/sistema.py` (`ParametroSistemaIn`/`Out`), `crud/parametro_sistema.py`
   (funciones sueltas: `list_todos`, `obtener`, `upsert`, `eliminar`, y
   `obtener_entero(db, clave, default)` — nunca lanza, castea a `int` o
   devuelve el default, pensado para ser reutilizado por cualquier
   consumidor futuro sin que tenga que manejar el caso "no configurado"),
   `api/v1/parametros_sistema.py` (`GET ""` sin paginar — mismo precedente
   que `/catalogos/roles`/`/sedes`, cualquier autenticado; `PUT ""` y
   `DELETE "/{clave}"` solo `ADMIN`, ni `LOGISTICA_CENTRAL` — respaldado
   por la fila de roles del diseño original: *"Administrador del sistema |
   Todos (config.) | Catálogos, usuarios, roles, **parámetros**,
   auditoría"*). `reportes.py::reporte_alertas` — `dias_vencimiento` pasa
   de `int = 30` a `int | None = None`; si es `None`, se resuelve con
   `await obtener_entero(db, "alertas_dias_vencimiento", default=30)`; el
   query param explícito sigue pudiendo pisarlo.
   **Frontend**: `components/administracion/ModuleTabs.tsx` gana un 4º
   tab ("Parámetros"); `ParametroSistemaForm.tsx`/
   `EliminarParametroSistemaButton.tsx`/`administracion/parametros/page.tsx`
   replican el patrón exacto de `ParametroStockForm.tsx`/
   `EliminarParametroButton.tsx`/`almacenes/parametros/page.tsx` de la
   Sesión 17 (`GET /parametros-sistema` es un array plano, no
   `Page<...>` — no se generó `PageParametroSistemaOut`, coherente con
   que tampoco existe para `/catalogos/roles` — así que la página no
   pagina, solo lista). El `DELETE` de este módulo también responde 204 y
   se benefició automáticamente del fix del proxy ya aplicado en la
   Sesión 17, sin tocar `route.ts` de nuevo.
   **Hallazgo real durante la verificación en el navegador** (no en los
   tests, que sí pasaban): `reportes/alertas/page.tsx` (Sesión 10) forzaba
   `dias_vencimiento = "30"` en el servidor cuando no había query param en
   la URL, y **siempre** lo mandaba explícito al backend
   (`query.set("dias_vencimiento", diasVencimiento)`) — es decir, el
   nuevo default configurable de `parametro_sistema` nunca se habría
   alcanzado desde esa pantalla real, aunque el backend y el test lo
   probaran correctamente de forma aislada. Corregido en la misma sesión
   (no se dejó como límite, porque conectar exactamente esa pantalla era
   el objetivo explícito del plan): `diasVencimiento` ahora es `""` si no
   hay query param, el `URLSearchParams` solo agrega `dias_vencimiento`
   si el usuario lo eligió explícitamente, y el `SelectFilter` ganó una
   opción `"Predeterminado del sistema"` (`value=""`) al inicio de la
   lista para reflejar ese estado.
   **Test nuevo**: `test_reportes.py::test_parametro_sistema_dias_vencimiento`
   — sin parámetro configurado, un lote a 10 días de vencer aparece con la
   ventana de 30 por defecto; `PUT /parametros-sistema` con
   `alertas_dias_vencimiento=5` por un rol no-ADMIN (`LOGISTICA_CENTRAL`)
   → 403; como ADMIN → 200; la misma consulta sin query param ahora
   excluye ese lote (10 > 5); `?dias_vencimiento=30` explícito lo sigue
   trayendo (el override de query sigue funcionando); `GET` con cualquier
   rol → 200; `DELETE` no-ADMIN → 403, ADMIN → 204; tras borrar, vuelve al
   comportamiento de 30 días. `pytest -q` completo: 31/31 en verde.
   Verificado de punta a punta en el navegador contra una base SQLite
   descartable con el seed real: login admin → `/administracion/parametros`
   → crear `alertas_dias_vencimiento=5` (`PUT`, 200) → aparece en la
   tabla → `/reportes/alertas` carga con la nueva opción "Predeterminado
   del sistema" sin forzar 30 → eliminar el parámetro (`DELETE`, 204,
   confirmado en Network que reutiliza el fix de proxy de la Sesión 17
   sin tocarlo) → la tabla vuelve a "No hay parámetros configurados". `npx
   tsc --noEmit` + `npx eslint .` + `npx next build` limpios (60 rutas,
   incluida `/administracion/parametros`).
   ~~**Sesión 19 — Conectar alerta_vigencia y alerta_saldo a
   parametro_sistema**~~ ✅ implementado. Backend-only, sin cambios de
   frontend ni de esquema (la forma JSON de las respuestas no cambia,
   solo cómo se calculan en el servidor — y `/administracion/parametros`,
   Sesión 18, ya es un formulario clave/valor genérico que soporta
   cualquier clave nueva sin tocar código). Cierra el límite consciente
   documentado en la Sesión 18 para dos de los tres campos agrupados ahí:
   `Contrato.alerta_vigencia` (RN-12, 30 días) y `ProductoContratado.
   alerta_saldo` (RN-12, 15%).
   **`ActaObservacion.plazo_vencido` (RN-11) se investigó primero y se
   descartó de esta sesión** (confirmado con el usuario antes de
   planear): a diferencia de los otros dos, no compara contra ningún
   número hardcodeado — solo `date.today() > self.plazo_subsanacion`, y
   `plazo_subsanacion` ya es un campo que el inspector fija libremente
   por acta al crearla (`ActaObservacionCreate.plazo_subsanacion`, RN-11).
   No hay ninguna constante "N días" que extraer a `parametro_sistema`;
   convertirlo en configurable habría exigido inventar un concepto de
   negocio nuevo (una ventana de gracia sobre un plazo que ya es
   configurable por acta) en vez de simplemente exponer un umbral
   existente — fuera del alcance de esta sesión, documentado como límite
   diferenciado del de la Sesión 18, no como trabajo pendiente.
   **Modelos** (`models/contratos.py`): los `@property alerta_vigencia`/
   `alerta_saldo` pasan a ser métodos `calcular_alerta_vigencia(self,
   umbral_dias: int = 30)`/`calcular_alerta_saldo(self, umbral_pct: int =
   15)` (mismo cuerpo, umbral parametrizado en vez de literal; default
   igual al valor hardcodeado original para no romper los asserts de
   `test_contratos.py` que no configuran nada). Confirmado con grep sobre
   todo `app/` que ningún otro archivo accedía a estos dos como atributo
   fuera de `models/contratos.py`/`schemas/contrato.py` — seguro
   convertirlos a método sin romper otros call sites.
   **Schemas** (`schemas/contrato.py`): `ContratoOut` gana su primer
   `from_model(cls, obj, umbral_alerta_vigencia)` explícito (antes era el
   único de los tres campos que dependía 100% de conversión implícita
   `from_attributes=True`, ni siquiera indirectamente vía otro
   `from_model`); `ContratoListOut.from_model` pasa a llamar
   `ContratoOut.from_model(obj, umbral)` en vez de
   `ContratoOut.model_validate(obj)`; `ProductoContratadoOut.from_model`
   (ya existía desde el Módulo 2) gana el parámetro `umbral_alerta_saldo`.
   **Endpoints** (`api/v1/contratos.py`): dos claves de módulo
   (`contratos_dias_alerta_vigencia`, `contratos_pct_alerta_saldo`),
   resueltas con `obtener_entero(db, clave, default=...)` (mismo helper
   de `crud/parametro_sistema.py` de la Sesión 18) en los 5 endpoints que
   devuelven alguno de los dos campos: `listar_contratos`,
   `obtener_contrato`/`crear_contrato` (vía `_build_detail`, que ahora
   recibe ambos umbrales), `agregar_producto_contratado` (solo umbral de
   saldo). **`cambiar_estado_contrato` es el único que cambia de
   estrategia de serialización, no solo de argumentos** — antes hacía
   `return contrato` (ORM crudo) con conversión automática vía
   `response_model=ContratoOut`; ahora construye
   `ContratoOut.from_model(contrato, umbral_vigencia)` explícito.
   **Test nuevo**: `test_contratos.py::
   test_parametro_sistema_alerta_vigencia_y_saldo` — sin configurar nada,
   un contrato a 15 días de vencer y un producto contratado al 100% de
   saldo se comportan igual que siempre (`alerta_vigencia=True` por el
   umbral de 30 por defecto, `alerta_saldo=False` por el de 15); `PUT
   /parametros-sistema` con `contratos_dias_alerta_vigencia=5` → el mismo
   contrato (15 días) pasa a `alerta_vigencia=False` tanto en el detalle
   como en el listado; `PUT` con `contratos_pct_alerta_saldo=100` → el
   producto contratado (100% de saldo) pasa a `alerta_saldo=True`;
   `PATCH .../estado` (cambio de estado) también refleja el umbral
   configurado. `pytest -q` completo: 32/32 en verde (mismo flake
   preexistente de `test_reportes.py::test_reportes_completo`, que no se
   disparó en esta corrida — ajeno a esta sesión). Verificado además con
   un backend descartable + llamadas directas por API contra un seed
   real: contrato de 15 días → `alerta_vigencia=true` por defecto →
   `PUT contratos_dias_alerta_vigencia=5` → `alerta_vigencia=false` en
   detalle, listado y `cambiar_estado_contrato` → `PUT
   contratos_pct_alerta_saldo=100` → `alerta_saldo=true` en el producto
   contratado → `DELETE` de ambos parámetros → vuelve exactamente al
   comportamiento por defecto (30 días / 15%). Sin verificación de
   navegador (sin cambios de frontend); `npx tsc --noEmit` + `npx
   eslint .` no aplican por el mismo motivo — no se tocó ningún archivo
   `.ts`/`.tsx`.
   ~~**Sesión 20 — Jobs automáticos RN-10/RN-11/RN-12**~~ ✅ implementado.
   Cierra el último punto grande documentado como pendiente: estas tres
   reglas piden "job automático"/"job diario" en el diseño original, y el
   proyecto no tenía ninguna infraestructura de scheduling ni de
   notificaciones. Investigado a fondo (2 agentes de exploración) antes de
   planear: **RN-10** ("cierre mensual") resultó ser una validación
   disparada por un usuario, no un cron — se implementó como un endpoint
   de solo lectura, sin infraestructura nueva. **RN-11** y **RN-12** sí
   piden ejecución automática periódica, así que se agregó
   **APScheduler** (`apscheduler==3.10.4`, `AsyncIOScheduler` in-process
   dentro del proceso `api` vía el `lifespan` de FastAPI — el
   `docker-compose.yml` no tiene ningún servicio worker separado y agregar
   uno habría sido sobre-ingeniería para una sola instancia sin réplicas).
   Sin infraestructura de email en el proyecto (confirmado con grep) —
   "Notificación a Logística" (RN-12) se materializa como una tabla
   `notificacion` nueva, consultable vía `GET /notificaciones`, no un
   correo real.
   **RN-11 es la primera mutación automática del backend sin acción de
   usuario** (cierra la OC y aplica penalidad sin revisión humana) — se
   diseñó para reutilizar al máximo `crud/informe_conformidad.py::
   cerrar_orden_compra`, ya existente y probado desde el Módulo 5 (Sesión
   9): el job solo marca la acta vencida como `RECHAZADA`
   (`crud/acta_observacion.py::vencer_automaticamente`, nuevo — mismo
   estado terminal que pondría un inspector con
   `registrar_reinspeccion(NO_CONFORME)`, pero sin pasar por una
   `Subsanacion` porque nunca llegó ninguna; no hay CHECK de DB que
   bloquee `ABIERTA -> RECHAZADA` directo) y llama la función ya
   existente — el cálculo de la `Penalidad` (monto = cantidad rechazada ×
   precio de la línea) no se reimplementó, se disparó solo. El bloque
   compartido de "la guía pasa a SUBSANADO si ya no le queda ninguna acta
   ABIERTA" se extrajo de `registrar_reinspeccion` a un helper
   `_actualizar_estado_guia`, reutilizado por ambos flujos (manual y
   automático) — sin duplicar el código de esa transición.
   **Auditoría (RN-08) de las mutaciones del job**: `core/audit.py::
   current_usuario_id` (el `ContextVar` que alimenta `AuditoriaLog`) solo
   se llena en requests HTTP vía `AuditContextMiddleware`; confirmado
   leyendo el código que si el job corre sin request, el evento
   `after_flush` simplemente no audita nada (no lanza, no inserta con
   `NULL` — `AuditoriaLog.usuario_id` no es nullable). Para que estas
   mutaciones sí queden auditadas (son cambios de negocio reales, no
   siembra), `core/jobs.py::procesar_actas_vencidas` fija
   `current_usuario_id` al `responsable_id` ya existente de la entidad que
   está tocando (el de la propia `ActaObservacion`/`OrdenCompra`) justo
   antes de cada mutación, y lo resetea después — sin inventar un
   "usuario de sistema" nuevo, reutilizando un FK ya válido y presente en
   la fila. Verificado con SQL logging que efectivamente se insertan filas
   en `auditoria_log` para `acta_observacion`, `penalidad`, `orden_compra`
   y `guia_remision` durante la corrida del job.
   **Esquema**: tabla nueva `notificacion` (`notificacion_id`, `tipo`,
   `referencia_id`, `mensaje`, `leida`, `creado_en` — sin FK a `usuario`,
   es un log de alertas, no un "documento" de RN-08, así que
   `procesar_alertas_contratos` no fija `current_usuario_id`), agregada a
   `db/init/01_schema.sql` + `db/patches_historicos/13_parche_notificacion.sql`.
   **Backend**: `models/notificacion.py`, `schemas/notificacion.py`,
   `crud/notificacion.py` (`CRUDNotificacion(CRUDBase)` +
   `existe_no_leida`/`marcar_leida`), `api/v1/notificaciones.py` (`GET`
   paginado + `PATCH .../leida`, roles `ADMIN, LOGISTICA_CENTRAL` — a
   quien está dirigida la alerta). `core/jobs.py` (nuevo):
   `procesar_actas_vencidas` (RN-11) y `procesar_alertas_contratos`
   (RN-12, reutiliza `Contrato.calcular_alerta_vigencia`/
   `ProductoContratado.calcular_alerta_saldo` y los umbrales de
   `parametro_sistema` de la Sesión 19; dedup: no re-notifica mientras la
   alerta previa siga sin marcarse `leida`). `core/scheduler.py` (nuevo):
   `AsyncIOScheduler` con dos jobs `cron` a horas fijas (02:00/03:00, sin
   volverlas configurables — RN-11/12 no lo piden), cada uno abre su
   propia sesión con `AsyncSessionLocal` y comitea. `main.py` pasa de
   wiring module-level a `lifespan=asynccontextmanager` — confirmado que
   `httpx.ASGITransport` (toda la suite de tests) no dispara el lifespan
   por defecto, así que los tests nunca arrancan el scheduler real.
   `crud/orden_compra.py::verificar_cierre_periodo` (RN-10): filtra
   `OrdenCompra.periodo_mes` por año+mes (columna client-supplied sin
   normalizar a día 1), separa terminales (`ANULADA`/`CERRADO`/
   `PENALIZADO` — el "PAGADO" del texto de RN-10 no es un estado de
   `OrdenCompra`, es de `InformeConformidadPago`, entidad separada) de
   pendientes; expuesto en `GET /ordenes-compra/cierre-mensual?anio=&mes=`,
   sin efectos secundarios (no hay entidad "periodo" en el esquema que
   cerrar).
   **Sin cambios de frontend** — una futura sesión podría agregar una
   pantalla para `/notificaciones`, documentado como próximo paso posible,
   no parte de esta sesión (el objetivo era cerrar el hueco de
   automatización backend). **Cerrado en la Sesión 21.**
   **Test nuevo**: `tests/test_jobs.py` (primer archivo que llama
   funciones de `core/jobs.py` directo con una `AsyncSession` cruda en vez
   de pasar por `httpx.AsyncClient` — estos jobs no tienen, ni deben
   tener, un endpoint HTTP que los dispare; el fixture `client` expone
   `client.session_factory` para abrir esa sesión cruda contra el mismo
   engine en memoria): caso de una sola línea observada con acta vencida
   → OC cierra sola `PENALIZADO` con `Penalidad` automática y guía
   `SUBSANADO`; caso de dos líneas donde solo una acta vence → la OC no
   se fuerza a cerrar (sigue `EMITIDA`, sin excepción no controlada);
   alertas de contrato con dedup (correr el job dos veces sin cambios no
   duplica, marcar `leída` sí dispara una nueva en la siguiente corrida).
   `test_compras.py` gana `test_cierre_mensual` para RN-10. `pytest -q`
   completo: 36/36 en verde. Verificado además con un backend descartable
   real: `uvicorn`/lifespan arrancan sin excepción (el scheduler se
   inicia limpio) → flujo completo por API hasta una acta con
   `plazo_subsanacion` vencido → job corrido directo contra el mismo
   archivo SQLite (mismo mecanismo que usaría APScheduler) →
   confirmado por API que el acta quedó `RECHAZADA`, la OC `PENALIZADO`,
   la guía `SUBSANADO`, la `Penalidad` con el monto correcto
   (220.0 = 40 × 5.5) y 2 filas nuevas en `auditoria_log` para
   `orden_compra` → job de RN-12 corrido igual, confirmado que crea las 2
   notificaciones esperadas → `GET /ordenes-compra/cierre-mensual` con la
   OC ya en estado terminal → `listo_para_cierre=true`.
   ~~**Sesión 21 — Pantalla /reportes/notificaciones**~~ ✅ implementado.
   Cierra el único punto pendiente que quedó documentado tras la Sesión
   20: el backend de RN-12 (`Notificacion`, `GET /notificaciones` +
   `PATCH .../leida`) se había implementado completo pero sin pantalla —
   con esto no queda ningún otro hueco grande documentado en CLAUDE.md.
   Frontend-only, sesión pequeña. **Ubicación**: 5º tab dentro de
   `/reportes` (`components/reportes/ModuleTabs.tsx`), no un ítem de nav
   nuevo — mismos roles exactos que el resto de esa sección (`ADMIN,
   LOGISTICA_CENTRAL`), y es donde ya vive `/reportes/alertas`, la
   pantalla más parecida en propósito. `app/(dashboard)/reportes/
   notificaciones/page.tsx` (nuevo, server component, mismo esqueleto que
   `reportes/auditoria/page.tsx`): tabla tipo/mensaje/fecha/estado +
   `<SelectFilter>` por `leida` (Todas/No leídas/Leídas) +
   `<Badge>` de tipo (`danger` para `CONTRATO_SALDO`, `warning` para
   `CONTRATO_VIGENCIA`) y de estado (`primary` "Nueva" / `neutral`
   "Leída"). `components/reportes/MarcarLeidaButton.tsx` (nuevo, client
   component) — mismo patrón que `EliminarParametroButton.tsx` (Sesión
   17) pero con el hook `PATCH` generado en vez de `DELETE`; solo se
   muestra en filas no leídas. **Sin formulario de creación** — las
   notificaciones solo las crea el job de la Sesión 20, nunca un
   usuario, mismo criterio que "Crear acta"/informes de conformidad (sin
   pantalla "nueva"). Primera vez que se regenera el cliente orval desde
   la Sesión 20 — ese backend nunca corrió `generate:api`, así que los
   hooks de `/notificaciones` no existían todavía en
   `lib/api/generated/`; confirmado el nombre exacto generado
   (`useMarcarNotificacionLeidaApiV1NotificacionesNotificacionIdLeidaPatch`)
   antes de escribir el botón. `npx tsc --noEmit` + `npx eslint .` + `npx
   next build` limpios (61 rutas, incluida `/reportes/notificaciones`).
   Verificado de punta a punta en el navegador contra un backend
   descartable: login admin → contrato con `fecha_fin`/saldo dentro de
   umbrales configurados (`PUT /parametros-sistema`, mismo mecanismo de
   la Sesión 19) → `core/jobs.py::procesar_alertas_contratos` corrido
   directo contra la misma base (mismo mecanismo de verificación manual
   de la Sesión 20, sin esperar al cron) → `/reportes/notificaciones`
   lista las 2 notificaciones generadas (`CONTRATO_VIGENCIA` con badge
   warning, `CONTRATO_SALDO` con badge danger, ambas "Nueva") → clic en
   "Marcar leída" → la fila pasa a "Leída" sin botón → filtro "No
   leídas" ya no la incluye. Backend sin cambios en esta sesión —
   `pytest -q` completo sigue en 36/36 (verificación de no-regresión, no
   se tocó ningún archivo `.py`).
   ~~**Fix del flake de `test_reportes_completo`**~~ ✅ corregido. Mencionado
   como "fragilidad ajena, preexistente" en 7 sesiones distintas desde la
   Sesión 12, nunca se había diagnosticado la causa exacta. Confirmado
   empíricamente (`SELECT datetime('now')` contra un engine SQLite en
   memoria vs. `datetime.now()`/`datetime.now(timezone.utc)` en el mismo
   proceso): `func.now()` en SQLite **siempre** devuelve UTC, sin importar
   la zona horaria del host. `IngresoAlmacen.fecha_ingreso` y
   `NotaSalida.fecha_salida` (`models/inventario.py`, `models/cocina.py`)
   usan `server_default=func.now()` — pero
   `crud/reportes.py::comparativo_consumo` compara esas columnas contra
   `fecha_inicio`/`fecha_fin`, y `test_reportes.py::test_reportes_completo`
   los calculaba con `date.today()` (hora **local** del proceso de test).
   Cualquier corrida que cayera en la ventana en que el día local y el día
   UTC difieren (todo el rango horario entre ambas medianoches, ancho según
   el huso del host — confirmado de ~5h en este entorno) hacía que la fila
   recién insertada quedara fuera de la ventana de fechas, dando
   `cantidad_recibida`/`cantidad_despachada = 0` en vez de los valores
   esperados. Es un desajuste de **test**, no un bug de producción (el
   reporte en sí no tiene una política de zona horaria documentada que
   violar). Fix acotado al test: `fecha_inicio`/`fecha_fin` ahora se
   calculan con `datetime.now(timezone.utc).date()` — el mismo reloj que
   usa `func.now()` — en vez de `date.today()`. No se tocó
   `crud/reportes.py` ni ningún modelo. `pytest -q` completo: 36/36 en
   verde.
   ~~**Deuda técnica: nombre de usuario en Auditoría**~~ ✅ corregido.
   Documentado desde la Sesión 10: `/reportes` → Auditoría mostraba
   "Usuario #N" porque `AuditoriaLogOut` solo exponía `usuario_id` — el
   razonamiento original decía que cruzar con `/usuarios` daría 403 para
   `LOGISTICA_CENTRAL` (`ADMIN`-only). Ese razonamiento describía cruzar
   desde el **frontend**; no aplica al backend, que ya tiene el FK
   `usuario_id -> usuario.usuario_id` y puede unir directo sin pasar por
   ningún endpoint. `models/auditoria.py::AuditoriaLog` gana
   `usuario: Mapped["Usuario"] = relationship(lazy="joined")` (nunca
   lazy-load en async, gotcha #1). **Restricción real encontrada al
   investigar**: ningún test de la suite siembra una fila `Usuario` real
   — todos emiten JWTs directo con `create_access_token(usuario_id=N)`
   sin insertar esa fila, y SQLite nunca tiene `PRAGMA foreign_keys=ON`
   en este proyecto, así que esas referencias colgantes funcionan hoy sin
   error; con un JOIN normal, `obj.usuario` sería `None` para casi toda
   la suite existente. `schemas/auditoria.py::AuditoriaLogOut` gana
   `usuario_nombre: str` + `from_model` (mismo patrón que
   `ContratoListOut.from_model`) con fallback explícito
   `f"Usuario #{obj.usuario_id}"` cuando `obj.usuario is None` — no es
   defensividad de más, es necesario para no romper la suite.
   `api/v1/auditoria.py::listar_auditoria` pasa de conversión automática
   a `AuditoriaLogOut.from_model(item)` explícito. `tests/test_compras.py`
   — el fixture `client` compartido (importado por ~8 archivos de test)
   gana `ac.session_factory = TestSession` expuesto en la instancia, para
   que tests que sí necesitan sembrar datos reales (como éste) puedan
   abrir una sesión cruda sin duplicar la construcción del engine.
   `tests/test_auditoria.py` gana un assert del fallback y un test nuevo
   que siembra `Rol`+`Usuario` reales y confirma `usuario_nombre` trae el
   nombre real. Frontend: `reportes/auditoria/page.tsx` — columna
   "Usuario" pasa de `Usuario #{log.usuario_id}` a `log.usuario_nombre`;
   regenerado el cliente orval. `pytest -q` completo: 37/37 en verde.
   `npx tsc --noEmit` + `npx eslint .` + `npx next build` limpios.
   Verificado de punta a punta en el navegador contra un backend
   descartable con el seed real: crear un producto → `/reportes/
   auditoria` muestra "Administrador SIGA-UNMSM" (el nombre real del
   admin sembrado) en vez de "Usuario #1".
   ~~**Deuda técnica: enriquecer detalle_json en Auditoría**~~ ✅
   corregido. `AuditoriaLog.detalle_json` existía en el esquema desde la
   Sesión 10 pero siempre quedaba `NULL` — el evento global
   (`core/audit.py::_registrar_auditoria`) solo registraba
   entidad/acción/actor, nunca qué cambió ("mejora futura, no
   bloqueante"). Ahora calcula el diff real: snapshot completo de
   columnas en `CREAR`/`ELIMINAR`, `{"columna": {"antes":..., "despues":
   ...}}` solo de las columnas que cambiaron en `ACTUALIZAR` (vía
   `state.attrs[key].history`).
   **Riesgo investigado antes de implementar** (CLAUDE.md gotcha #7.3:
   columnas `GENERATED ALWAYS ... STORED`, ej. `ProductoContratado.
   tope_monetario`, quedan "expiradas" tras el INSERT y leerlas sin
   refrescar revienta en async): confirmado empíricamente con un modelo
   mínimo que en SQLite (motor de los tests) `INSERT ... RETURNING` ya
   las resuelve (`inspect(obj).unloaded` vacío justo tras el flush) —
   pero el gotcha describe MySQL/aiomysql (producción), que no resuelve
   `RETURNING` igual, así que ahí sí quedan expiradas. Como el evento
   corre para *toda* sesión en *todo* entorno, `_snapshot`/`_diff` filtran
   `attr.key in state.unloaded` antes de leer cualquier columna — en
   SQLite ese chequeo nunca excluye nada (por eso los tests no lo
   detectarían solos), en MySQL sí evita el crash. Se verificó además
   que la suite completa (37 tests, todos los módulos) sigue en verde
   tras el cambio — el evento corre para *todas* las entidades de *todos*
   los módulos, así que cualquier columna `Computed`/relación mal cubierta
   habría fallado en cualquier archivo, no solo en `test_auditoria.py`.
   **Dato sensible excluido**: `Usuario.password_hash` (única columna
   sensible en todo el esquema, confirmado con `grep -rn "password\|
   secret\|token" app/models/*.py`) nunca aparece en `detalle_json`, ni
   siquiera como hash — `CAMPOS_EXCLUIDOS` en `core/audit.py`.
   `tests/test_auditoria.py`: asserts del snapshot completo en `CREAR`,
   del diff acotado (solo la columna que cambió) en `ACTUALIZAR`, y un
   caso que actualiza un `Usuario` real vía `PATCH /usuarios/{id}`
   confirmando que `password_hash` no aparece en su `detalle_json`.
   `pytest -q` completo: 37/37 en verde. Verificado además en el
   navegador contra un backend descartable con el seed real: crear +
   editar un producto → `/reportes/auditoria` muestra el `pre` (ya
   renderizado desde la Sesión 10) con el snapshot completo en la fila
   `CREAR` y el diff exacto (`{"nombre": {"antes":..., "despues":...}}`)
   en la fila `ACTUALIZAR`, sin `codigo` ni otras columnas sin tocar. Sin
   cambios de schema/endpoint/frontend — solo `core/audit.py`.
   ~~**Deuda técnica: filtros de /reportes (sede, proveedor, producto)**~~
   ✅ corregido. Documentado desde la Sesión 10: el diseño original
   (línea 110: "Reportes por periodo/contrato/proveedor/producto/centro
   de consumo"; línea 545: "filtros estándar... almacén, sede, comedor,
   proveedor, producto") prometía más filtros de los que `reportes.py`
   implementaba (solo `almacen_id`/`producto_id`+fechas). Investigado
   antes de implementar en vez de agregar todos los filtros "estándar" a
   los 3 endpoints por igual: no todos aplican con el mismo sentido a las
   4 métricas de `comparativo_consumo` (teórico/comprado/recibido/
   despachado) — un `centro_consumo_id`, por ejemplo, tendría sentido para
   "despachado" y parcialmente para "teórico", pero no para "comprado"
   (`OrdenCompra` es multialmacén/distribuido, RN-15/19, sin un
   centro_consumo único) — agregarlo de todas formas habría sido un
   filtro que calladamente no filtra una de las 4 cifras. Se priorizó en
   cambio un filtro nuevo por endpoint, cada uno 100% aplicable a todo lo
   que ese endpoint devuelve: `valorizacion-inventario` gana `sede_id`
   (`Almacen.sede_id`, columna ya existente); `comparativo-consumo` gana
   `proveedor_id`, aplicado **solo** a `cantidad_comprada` (única de las
   4 métricas con dimensión de proveedor real, vía
   `OrdenCompra.contrato_id -> Contrato.proveedor_id` — documentado en el
   docstring de `crud/reportes.py::comparativo_consumo` por qué las otras
   3 no lo usan); `alertas` gana `producto_id`, aplicado por igual a los
   3 sub-reportes (los tres ya unen contra `Producto`). `centro_consumo_id`
   queda fuera, documentado como límite consciente por la razón de
   arriba, no una omisión. Sin cambios de schema de salida (son filtros de
   `WHERE`, no columnas nuevas). Frontend: mismo patrón `<SelectFilter>`/
   formulario ya usado en cada página — `reportes/page.tsx` gana un
   segundo `<SelectFilter>` (`sede_id`, alimentado por
   `GET /catalogos/sedes`); `ComparativoConsumoForm.tsx` gana un `<select>`
   de proveedor (`GET /proveedores?page_size=100`), con el texto de la
   opción "Todos" aclarando que solo filtra "Comprado" para no confundir
   sobre las otras 3 métricas; `reportes/alertas/page.tsx` gana un
   `<SelectFilter>` de producto (`GET /productos?page_size=100`). Tests
   nuevos en `test_reportes.py` (mismo patrón "dos X independientes" ya
   usado para RN-20/proveedor en Sesiones 11/12/15/16): dos almacenes en
   sedes distintas para `sede_id`; dos proveedores contratando el mismo
   producto para `proveedor_id` (confirma que el filtro solo mueve
   `cantidad_comprada`, no las otras 3 métricas); dos productos con stock
   bajo en el mismo almacén para `producto_id`. `tests/test_cocina.py`
   gana `ac.session_factory = TestSession` expuesto en el fixture `client`
   (mismo patrón ya aplicado a `test_compras.py` en el fix anterior),
   necesario para sembrar una sede/almacén adicional fuera del flujo HTTP
   en el test de `sede_id`. `pytest -q` completo: 40/40 en verde. `npx tsc
   --noEmit` + `npx eslint .` + `npx next build` limpios (mismas 61
   rutas, sin rutas nuevas — solo cambios de filtro). Verificado de punta
   a punta en el navegador contra un backend descartable con el seed real
   (3 sedes/4 almacenes reales): el `<SelectFilter>` de sede en
   `/reportes` navega a `?sede_id=1` (200, sin error); el de producto en
   `/reportes/alertas` se renderiza vacío hasta crear un producto de
   prueba, luego aparece en las opciones; el de proveedor en
   `/reportes/comparativo` — tras crear un producto y un proveedor de
   prueba — se renderiza con la razón social real y la consulta con
   `proveedor_id` explícito responde 200 con las 4 métricas en 0 (sin
   datos de compra en la base descartable, comportamiento esperado).

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
