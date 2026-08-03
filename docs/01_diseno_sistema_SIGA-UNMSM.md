# SIGA-UNMSM
## Sistema Integral de Gestión de Almacén y Abastecimiento Alimentario
### Universidad Nacional Mayor de San Marcos

**Documento de diseño de sistema** · Arquitectura de información, flujos de usuario, modelo de datos y reglas de negocio

---

## 1. Visión general y principios de diseño

El sistema garantiza **trazabilidad extremo a extremo** de cada insumo alimentario, desde la planificación anual hasta el pago al proveedor, siguiendo la cadena:

```
Requerimiento Anual → Contrato → Producto Contratado → Orden de Compra →
Pedido Semanal → Guía de Remisión → Inspección → Acta de Observación (si aplica) →
Ingreso a Almacén (Kardex/Bin Card) → Nota de Salida a Cocina →
Consumo → Conformidad → Informe de Pago
```

Tres principios rigen cada módulo:

1. **Ningún movimiento sin origen documentado.** Toda guía, ingreso o salida debe enlazarse a un documento padre (orden de compra, pedido, solicitud).
2. **Ningún saldo se toca dos veces sin verificación.** Cantidad y monto contractual, de orden de compra y de stock se validan antes de cada transacción, nunca después.
3. **Ninguna observación bloquea lo que sí es conforme.** Las retenciones de pago son por producto/línea, no por orden de compra completa.

### 1.1 Paleta y lenguaje visual (referencia para todas las pantallas)

| Uso | Color | Hex aprox. |
|---|---|---|
| Color institucional primario | Azul UNMSM | `#003DA5` |
| Azul secundario / hover | Azul medio | `#0057B8` |
| Fondo general | Blanco | `#FFFFFF` |
| Superficies / tarjetas | Gris neutro claro | `#F2F4F7` |
| Texto secundario / bordes | Gris neutro | `#6B7280` |
| Estado: Conforme / OK | Verde | `#1E8E3E` |
| Estado: Pendiente / en proceso | Amarillo | `#F2A900` |
| Estado: Observado / Retenido | Rojo | `#D93025` |
| Estado: Cerrado / Anulado | Gris oscuro | `#4B5563` |

Tipografía: fuente institucional sans-serif de alta legibilidad (p. ej. Source Sans / Inter), jerarquía clara de encabezados, tablas densas con alto contraste para uso administrativo prolongado.

---

## 2. Roles y permisos

| Rol | Módulos con acceso completo | Acciones clave |
|---|---|---|
| Administrador del sistema | Todos (config.) | Catálogos, usuarios, roles, parámetros, auditoría |
| Planificación / Nutrición | M1, M1A | Crea/aprueba menús, raciones, BOM; **el Nutricionista autorizado** además mantiene el catálogo nutricional y las recetas institucionales |
| Logística / Abastecimiento | M2, M3 (OC), M5 | Proveedores, contratos, órdenes de compra, informes de pago |
| Almacenero | M3 (ingresos), M4 | Recepciones, kardex, bin card, notas de salida |
| Inspector de calidad/cantidad | M3 (inspección) | Actas de observación, subsanaciones |
| Personal de cocina | M4 (solicitudes) | Solicitudes diarias, consulta de menú del día |
| Abastecimiento/Pagos | M5 (recepción informe) | Registra estado de pago |
| Proveedor (portal externo, solo lectura + carga de guía) | M2 (consulta), M3 (guías) | Ve sus contratos, cronograma, sube guías, ve observaciones |

Control de acceso: RBAC por módulo + regla de "cuatro ojos" (quien registra un ingreso no puede ser quien aprueba la conformidad de pago de la misma orden).

**Alcance por almacén (RN-20).** Todo usuario operativo (almacenero, inspector, cocina) tiene una lista explícita de almacenes autorizados (`usuario_almacen_acceso`) y solo ve/opera sobre esos almacenes. Los perfiles **Administrador del sistema** y **Logística/Abastecimiento central** tienen acceso irrestricto a todos los almacenes y sedes, con capacidad de consolidar y comparar entre ellos.

---

## 3. Arquitectura de información (mapa del sitio)

```
SIGA-UNMSM
├── 00 Dashboard ejecutivo
├── 01 Planificación anual
│   ├── Raciones y población atendida
│   ├── Menús quincenales
│   ├── Explosión de materiales (BOM)
│   └── Requerimiento anual consolidado
├── 01A Dosificación nutricional y preparaciones
│   ├── Catálogo nutricional de alimentos (Tabla Peruana + institucional)
│   ├── Recetas / preparaciones institucionales
│   ├── Cálculo nutricional por receta y por ración
│   ├── Dosificación automática por menú, día, comedor y almacén
│   └── Explosión de materiales por semana/quincena/mes/año
├── 02 Proveedores y contratos
│   ├── Maestro de proveedores
│   ├── Contratos
│   └── Productos contratados / precios / topes / saldos
├── 03 Compras
│   ├── Órdenes de compra mensuales
│   └── Pedidos semanales / dosificados
├── 04 Recepción y calidad
│   ├── Guías de remisión
│   ├── Inspección de calidad y cantidad
│   ├── Actas de observación
│   └── Subsanaciones
├── 05 Almacenes (multialmacén)
│   ├── Maestro de almacenes (4 almacenes: C.U., Cangallo, Veterinaria, Adm./Docentes)
│   ├── Ubicaciones internas (zona/estante/nivel/cámara) por almacén
│   ├── Ingresos por almacén
│   ├── Kardex valorizado por almacén
│   ├── Bin card por almacén
│   ├── Ajustes, mermas, devoluciones e inventario físico
│   ├── Transferencias entre almacenes
│   ├── Alertas por almacén (stock mínimo, vencimiento, observados, diferencias)
│   └── Seguimiento guías vs. órdenes de compra
├── 06 Cocina y consumo
│   ├── Solicitudes diarias
│   ├── Notas de salida
│   └── Consumo teórico vs. real
├── 07 Conformidad y pagos
│   ├── Retenciones y penalidades
│   ├── Informes de conformidad para pago
│   └── Seguimiento de estado de pago (Abastecimiento)
├── 08 Reportes y auditoría
│   ├── Reportes por periodo / contrato / proveedor / producto / centro de consumo
│   └── Bitácora de auditoría (log inalterable)
└── 09 Administración
    ├── Usuarios y roles
    ├── Catálogos (productos, unidades, centros de consumo, sedes)
    └── Parámetros del sistema
```

---

## 4. Flujos de usuario por módulo

### 4.1 Módulo 1 — Planificación estratégica anual

```
[Nutrición] define Raciones anuales (sede, población, periodo)
        │
        ▼
[Nutrición] crea Menú quincenal (platos, ingredientes, cantidad/ración)
        │
        ▼
Sistema ejecuta Explosión de Materiales (BOM)
   insumo = Σ (cantidad_por_racion × raciones_programadas) por periodo
        │
        ▼
Sistema consolida Requerimiento Anual de Insumos
   (cantidad estimada, unidad, presupuesto referencial)
        │
        ▼
[Nutrición] envía a aprobación → [Administrador/Logística] aprueba
        │
        ▼
Estado: BORRADOR → EN_REVISION → APROBADO → VIGENTE
(cada cambio genera una nueva versión; las anteriores quedan de solo lectura)
```
Regla clave: el requerimiento anual **aprobado** es el techo contra el cual se validarán todos los contratos posteriores.

### 4.1A Módulo 1A — Dosificación nutricional y gestión de preparaciones

#### Catálogo nutricional (base de alimentos)

```
Importación inicial: Tabla Peruana de Composición de Alimentos
        │
        ▼
Sistema crea Alimento (código, nombre, categoría, tipo = BASE_TABLA)
   + Alimento_Version 1 (valores por 100 g, fuente, fecha de importación, vigente = true)
        │
        ▼
[Nutricionista autorizado] puede:
   • Crear alimentos adicionales (tipo = PREPARADO_IMPORTADO o PREPARACION_INSTITUCIONAL)
   • Corregir valores nutricionales → genera Alimento_Version N+1
     (la versión anterior queda histórica, vigente = false; nunca se borra)
   • Desactivar un alimento (estado = INACTIVO, sin eliminar histórico)
```

Cada alimento conserva como mínimo, por 100 g: energía (kcal y kJ), agua, proteínas, grasa total, carbohidratos totales y disponibles, fibra dietaria, cenizas, calcio, fósforo, zinc, hierro, vitamina A, tiamina, riboflavina, niacina, vitamina C, ácido fólico, sodio y potasio.

#### Gestión de preparaciones (recetas institucionales)

```
[Nutricionista] crea Receta (código, nombre, categoría: sopa/segundo/entrada/
   bebida/postre, N° raciones base, tamaño de porción, rendimiento %,
   merma estimada %, procedimiento, adjuntos: foto/ficha técnica)
        │
        ▼
[Nutricionista] agrega Ingredientes (1..N alimentos del catálogo)
   por cada ingrediente: cantidad bruta, cantidad neta, unidad,
   factor de conversión, merma
        │
        ▼
VALIDACIÓN: la receta debe tener ≥ 1 ingrediente y rendimiento > 0 (RN-23)
        │
        ▼
Sistema calcula automáticamente, agregando los valores nutricionales
vigentes de cada alimento según su cantidad neta:
   Aporte nutricional TOTAL de la receta = Σ (cantidad_neta_i / 100 × valor_nutricional_i)
   Aporte POR RACIÓN = Aporte total / N° de raciones base
        │
        ▼
Flujo de estados: BORRADOR → EN_REVISION → APROBADO → VIGENTE → DESCONTINUADO
```

**Versionamiento (RN-25):** una receta `APROBADO`/`VIGENTE` ya usada en algún menú **no se edita**. Cualquier ajuste (ingrediente, cantidad, procedimiento) crea una nueva versión (`receta_padre_id` apunta a la versión anterior); los menús ya programados conservan la versión con la que fueron calculados, preservando la auditoría histórica.

#### Dosificación automática y explosión de materiales (BOM)

```
[Nutrición] arma Menú Quincenal seleccionando SOLO recetas en estado
   VIGENTE (RN-22), y define raciones programadas por día, comedor y almacén
        │
        ▼
Sistema calcula, por cada (receta × menú_día × comedor/almacén):
   cantidad_bruta_requerida = raciones_programadas × (tamaño_porción / rendimiento) ×
                                cantidad_bruta_ingrediente × (1 + %merma)
   (aplicando también el factor de conversión de unidad del ingrediente)
        │
        ▼
Sistema consolida la Dosificación Detalle → Explosión de Materiales (BOM)
   agregable por: SEMANA · QUINCENA · MES · AÑO, y por ALMACÉN
        │
        ▼
Sistema compara el requerimiento teórico contra:
   • Stock disponible del almacén correspondiente
   • Stock comprometido (reservas existentes)
   • Saldo contractual global del producto
        │
        ├── Suficiente ──────────► genera Pedido Semanal Dosificado por almacén
        │
        └── Insuficiente ────────► Alerta (RN-28): dosificación supera stock
                                     disponible o saldo contractual; no bloquea
                                     la planificación pero exige decisión de Logística
        │
        ▼
Al despachar en cocina (Módulo 4), el sistema compara el Consumo Real
(notas de salida) contra el Consumo Teórico (dosificación de la receta),
mostrando diferencias, mermas y sobrantes por preparación y por comedor
```

#### Reglas de negocio — dosificación nutricional

| # | Regla |
|---|---|
| RN-22 | Solo recetas en estado `VIGENTE` pueden incorporarse a un menú |
| RN-23 | Toda receta debe tener ≥ 1 ingrediente y `rendimiento_pct > 0` |
| RN-24 | Cantidad requerida por ingrediente = f(raciones programadas, tamaño de porción, rendimiento, merma, factor de conversión) |
| RN-25 | Menú y receta conservan versión histórica inmutable; una receta aprobada y usada no se edita, se versiona |
| RN-26 | Cambios en valores nutricionales o ingredientes de receta solo por el rol **Nutricionista autorizado**, con registro en `auditoria_log` |
| RN-27 | Los pedidos semanales dosificados se generan de forma independiente por cada combinación (almacén, comedor) |
| RN-28 | El sistema advierte (no bloquea la planificación) si la dosificación proyectada supera el stock disponible o el saldo contractual del producto |

#### Pantallas del Módulo 1A

21. **Catálogo nutricional** — tabla de alimentos con filtro por categoría/tipo/estado, ficha de detalle con los 20 valores por 100 g y su historial de versiones.
22. **Recetas / preparaciones** — listado por categoría y estado, con línea de tiempo de versiones.
23. **Editor de receta** — formulario de ingredientes + panel de cálculo nutricional en vivo (total y por ración), adjuntos de foto/ficha técnica.
24. **Dosificación y BOM por periodo** — vista consolidable por semana/quincena/mes/año y por almacén, con semáforo de suficiencia de stock/saldo contractual.

---

### 4.2 Módulo 2 — Gestión contractual

```
[Logística] registra Proveedor (RUC, razón social, documentos)
        │
        ▼
[Logística] crea Contrato ligado a Proveedor + Requerimiento Anual
   (vigencia, presupuesto total, cronograma, penalidades)
        │
        ▼
[Logística] define Productos Contratados
   (producto, unidad, precio unitario, cantidad contratada = tope físico,
    tope monetario = precio × cantidad)
        │
        ▼
Sistema inicializa Saldo físico = cantidad contratada
             Saldo monetario = tope monetario
        │
        ▼
Alertas automáticas cuando:
  • vigencia ≤ 30 días de vencer
  • saldo físico ≤ 15% del tope
  • saldo monetario ≤ 15% del tope
```

### 4.3 Módulo 3 — Ciclo mensual de compra y recepción

```
[Logística] genera Orden de Compra (mes, contrato, productos, cantidades)
        │
        ▼
VALIDACIÓN OBLIGATORIA: cantidad×precio ≤ saldo monetario del contrato
                         cantidad ≤ saldo físico del contrato
        │  (si falla → bloqueo, mensaje de saldo insuficiente)
        ▼
Sistema descuenta saldo contractual RESERVADO (no consumido aún)
        │
        ▼
[Logística/Nutrición] genera Pedido Semanal a partir del Menú Quincenal
   vigente + raciones programadas + stock disponible en almacén
        │
        ▼
[Proveedor] entrega insumos → sube/registra Guía de Remisión
   (vinculada obligatoriamente a 1 Orden de Compra + 1 Pedido Semanal)
        │
        ▼
[Inspector] realiza Inspección de calidad y cantidad por línea de producto
        │
        ├── TODO CONFORME ─────────────► Ingreso TOTAL a almacén
        │
        └── HAY DISCONFORMES ──────────► Acta de Observación
                (producto, lote, cantidad observada, motivo, evidencia,
                 responsable, plazo de subsanación)
                        │
                        ▼
              Ingreso PARCIAL (solo lo conforme) a almacén
        │
        ▼
Sistema actualiza automáticamente:
   Kardex valorizado · Bin card · Stock disponible ·
   Saldo de Orden de Compra · Saldo contractual (consumo real)
        │
        ▼
Estado de guía: PENDIENTE → PARCIAL → CONFORME / OBSERVADO →
                 SUBSANADO → CERRADO / PENALIZADO
```

### 4.4 Módulo 4 — Distribución y consumo

```
[Cocina] revisa Menú del día → genera Solicitud Diaria de Insumos
        │
        ▼
Sistema valida stock disponible por producto
        │  (si insuficiente → bloqueo, sugiere sustituto o alerta a Logística)
        ▼
[Almacenero] aprueba y emite Nota de Salida de Almacén
        │
        ▼
Sistema descuenta stock, registra salida en Kardex valorizado,
actualiza Bin card
        │
        ▼
Sistema calcula Consumo Teórico (según BOM del menú del día)
  vs. Consumo Real (según notas de salida) → variación %
```

### 4.5 Módulo 5 — Control y pagos

```
Sistema evalúa Orden de Compra al cierre del periodo de entrega
        │
        ├── ¿Tiene actas de observación pendientes?
        │
   SÍ ──┼── [Proveedor] presenta Subsanación (evidencia)
        │        │
        │        ▼
        │   [Inspector] re-inspecciona
        │        │
        │   ┌────┴────┐
        │   OK          NO OK (fuera de plazo)
        │   │             │
        │   Levanta        Cierra OC con cantidad menor,
        │   observación    aplica penalidad, deja motivo
        │   │             │
        └───┴─────────────┘
                │
   NO / YA LEVANTADAS
                │
                ▼
Sistema genera Informe de Conformidad para Pago
  (proveedor, contrato, OC, guías, productos conformes, montos,
   productos retenidos, penalidades, firmas)
                │
                ▼
[Logística] deriva a Oficina de Abastecimiento
Estado: ENVIADO → RECIBIDO → EN_PROCESO_DE_PAGO → PAGADO / DEVUELTO
```

---

## 4.6 Módulo 6 — Gestión multialmacén y sedes

### 4.6.1 Maestro de almacenes

El sistema administra de forma **independiente y consolidada** los cuatro almacenes:

| Código | Almacén | Sede | Tipo de comedor |
|---|---|---|---|
| ALM-CU | Almacén Comedor de Alumnos — Ciudad Universitaria | Ciudad Universitaria | Estudiantes |
| ALM-CAN | Almacén Comedor de Alumnos — Cangallo | Cangallo | Estudiantes |
| ALM-VET | Almacén Comedor de Alumnos — Veterinaria | Veterinaria | Estudiantes |
| ALM-ADM | Almacén Comedor de Administrativos y Docentes | Ciudad Universitaria | Adm./Docentes |

Cada almacén registra: código, nombre, sede, dirección/ubicación, tipo de comedor, responsable, estado (ACTIVO/INACTIVO), y su propio catálogo de **ubicaciones internas** (zona → estante → nivel → contenedor/cámara de conservación, con indicador de cadena de frío para perecibles).

### 4.6.2 Principio de control: global vs. local

```
CONTRATO (saldo físico / monetario) ─────────► se controla de forma GLOBAL
                                                  (independiente del almacén)
        │
        ▼
ORDEN DE COMPRA ── se distribuye entre 1..N almacenes destino
        │
        ▼
STOCK, KARDEX, BIN CARD, CONSUMO, SOLICITUDES ─► se controlan de forma
                                                  LOCAL (por almacén)
```

Es decir: el proveedor negocia y factura contra el contrato como un todo, pero cada unidad física vive, se mueve y se consume dentro de un único almacén hasta que una **transferencia** la traslada explícitamente a otro.

### 4.6.3 Flujo — distribución de una orden de compra entre almacenes

```
[Logística] crea Orden de Compra sobre Contrato vigente
        │
        ▼
Por cada línea de producto, [Logística] distribuye la cantidad total
entre 1..N almacenes destino:
    Arroz superior · 700 KG → 400 KG a ALM-CU, 200 KG a ALM-CAN, 100 KG a ALM-VET
        │
        ▼
VALIDACIÓN: Σ(cantidad por almacén) = cantidad total de la línea de OC
        │
        ▼
Cada Guía de Remisión indica un único almacén de destino
   (una entrega física llega a un solo lugar)
        │
        ▼
El Ingreso a Almacén actualiza EXCLUSIVAMENTE:
   Kardex, Bin Card y Stock del almacén receptor indicado en la guía
```

### 4.6.4 Flujo — pedido semanal y solicitud de cocina (alcance local)

```
[Nutrición/Logística] genera Pedido Semanal
   = f(sede, menú, raciones programadas, ALMACÉN asignado a esa sede/comedor)
        │
        ▼
[Cocina de un comedor] genera Solicitud Diaria
   → vinculada EXCLUSIVAMENTE a su almacén y centro de consumo
        │
        ▼
Sistema valida stock disponible SOLO en ese almacén
        │
        ▼
Nota de Salida descuenta stock SOLO del almacén asignado a la cocina solicitante
   (no puede tomar stock de otro almacén, aunque tenga excedente)
```

### 4.6.5 Flujo — transferencia entre almacenes

```
[Almacenero origen] crea Nota de Transferencia de Salida
   (almacén origen, almacén destino, productos, cantidades, responsable, fecha)
        │
        ▼
Sistema descuenta stock del almacén ORIGEN
   (kardex + bin card origen: movimiento tipo TRANSFERENCIA_SALIDA)
   Estado: EN_TRANSITO
        │
        ▼
[Almacenero destino] registra Recepción de Transferencia
        │
        ├── Cantidad recibida = cantidad enviada ──► Estado: RECIBIDA_CONFORME
        │
        └── Diferencia (merma en tránsito, rotura) ──► Estado: RECIBIDA_CON_DIFERENCIA
                                                           + observación registrada
        │
        ▼
Sistema incrementa stock del almacén DESTINO
   (kardex + bin card destino: movimiento tipo TRANSFERENCIA_INGRESO)
        │
        ▼
Trazabilidad conservada: almacén origen, almacén destino, producto,
cantidad enviada, cantidad recibida, responsables (origen y destino), fechas, estado
```

### 4.6.6 Tipos de movimiento de inventario por almacén

Además de ingreso (compra) y salida (cocina), cada almacén registra de forma independiente:

- **Ajuste** — corrección positiva/negativa con motivo y responsable (nunca sobrescribe, siempre inserta un nuevo movimiento).
- **Merma** — pérdida por deterioro, vencimiento o rotura; requiere motivo y, si aplica, evidencia.
- **Devolución** — a proveedor (sale del almacén, referencia a guía/acta) o de cocina (regresa al almacén, referencia a nota de salida).
- **Inventario físico** — conteo periódico programado; el sistema compara `stock_sistema` vs. `conteo_fisico` y genera automáticamente un ajuste por la diferencia, dejando registro de quién contó y cuándo.

### 4.6.7 Stock por almacén — tres cantidades independientes

| Cantidad | Significado |
|---|---|
| **Stock físico** | Lo que existe materialmente en el almacén, según kardex |
| **Stock comprometido** | Reservado por solicitudes de cocina aprobadas pendientes de despacho, o por transferencias salientes en tránsito |
| **Stock disponible** | `Stock físico − Stock comprometido` — es el número contra el que se valida toda nueva solicitud o transferencia |

### 4.6.8 Reglas de negocio multialmacén

| # | Regla |
|---|---|
| RN-13 | Toda guía de remisión e ingreso debe indicar `almacen_destino_id` obligatorio |
| RN-14 | Un ingreso actualiza kardex/bin card/stock únicamente del almacén receptor de esa guía |
| RN-15 | `Σ cantidad_por_almacén (orden_compra_distribucion) = cantidad_solicitada` de la línea de OC |
| RN-16 | Pedido semanal se calcula por combinación única de (sede, menú, almacén) |
| RN-17 | Nota de salida solo descuenta el almacén asignado a la cocina/centro de consumo solicitante |
| RN-18 | Toda transferencia requiere nota de salida (origen) + recepción (destino); el stock destino solo se incrementa al confirmarse la recepción, nunca al emitirse la salida |
| RN-19 | El saldo contractual (físico/monetario) se valida de forma global por contrato, independientemente de cuántos almacenes reciban producto de esa orden |
| RN-20 | Un usuario operativo solo accede a los almacenes listados en `usuario_almacen_acceso`, salvo rol Administrador o Logística central |
| RN-21 | Stock disponible = stock físico − stock comprometido; toda solicitud/transferencia valida contra el disponible, no contra el físico |

### 4.6.9 Pantallas del módulo multialmacén (se suman al catálogo de la sección 6)

15. **Maestro de almacenes** — ficha por almacén (código, sede, responsable, tipo de comedor, estado) y su árbol de ubicaciones internas.
16. **Dashboard consolidado con filtro por almacén** — mismos KPIs de la sección 6.1, con selector de almacén/sede/comedor que recalcula todos los indicadores.
17. **Distribución de orden de compra por almacén** — tabla editable: producto × almacén destino, con validación de suma = cantidad total.
18. **Transferencias entre almacenes** — bandeja de transferencias emitidas/recibidas, estado (en tránsito, recibida conforme, con diferencia).
19. **Ajustes, mermas, devoluciones e inventario físico** — formulario por almacén con motivo, evidencia y responsable.
20. **Alertas por almacén** — stock mínimo, productos por vencer, observados y diferencias de inventario, filtrable por almacén.

### 4.6.10 Reportes multialmacén

- Stock consolidado (todos los almacenes) y stock detallado por almacén.
- Kardex por almacén, producto y rango de fechas.
- Consumo por comedor, sede, menú y número de raciones.
- Comparativo: requerimiento planificado vs. compra vs. recepción vs. consumo real, por sede.
- Transferencias entre almacenes (emitidas, recibidas, en tránsito, con diferencia).
- Productos próximos a vencer, con bajo stock o con observaciones, por almacén.
- Valorización de inventario por almacén y consolidada.

Todos estos reportes reutilizan los filtros estándar del sistema (fecha, almacén, sede, comedor, producto, proveedor) definidos en la sección 6.

---

## 5. Reglas de validación (motor de reglas)

| # | Regla | Disparador | Efecto |
|---|---|---|---|
| RN-01 | `cantidad_OC × precio ≤ saldo_monetario_contrato` y `cantidad_OC ≤ saldo_fisico_contrato` | Al emitir Orden de Compra | Bloquea emisión; muestra saldo disponible |
| RN-02 | Toda guía requiere `id_orden_compra` y `id_pedido_semanal` no nulos | Al registrar Guía de Remisión | Bloquea guardado |
| RN-03 | `cantidad_ingresada ≤ cantidad_solicitada` salvo `autorizacion_excedente_id` no nulo | Al registrar ingreso | Bloquea o exige autorización documentada |
| RN-04 | Solo `estado_linea = 'CONFORME'` incrementa stock disponible | Post-inspección | Ingresa a Kardex |
| RN-05 | `estado_linea = 'OBSERVADO'` excluye la línea de la Conformidad de Pago hasta `subsanado` o `cerrado_penalizado` | Generación de Informe de Pago | Retiene solo la línea afectada |
| RN-06 | Todo `movimiento_kardex` es insert-only (sin UPDATE/DELETE); correcciones = movimiento de ajuste con referencia | Cualquier movimiento de inventario | Trazabilidad inalterable |
| RN-07 | `cantidad_nota_salida ≤ stock_disponible` | Al emitir Nota de Salida | Bloquea emisión |
| RN-08 | Todo documento requiere `numero_correlativo`, `estado`, `responsable_id`, `fecha`, `adjuntos[]`, `historial_auditoria[]` | Creación de cualquier documento | Validación de esquema obligatoria |
| RN-09 | `precio_unitario_OC = precio_unitario_contrato_vigente` (no editable manualmente) | Al agregar línea a Orden de Compra | Autocompletado y bloqueado |
| RN-10 | Cierre mensual solo si todas las OC del periodo están en estado terminal (`CERRADO`, `PAGADO`, `PENALIZADO`) | Proceso de cierre mensual | Bloquea cierre; lista pendientes |
| RN-11 | Plazo de subsanación vencido sin respuesta → job automático cierra OC con cantidad conforme y aplica penalidad según contrato | Job diario / cron | Cierre automático + notificación |
| RN-12 | Alerta de contrato (vigencia, saldo físico, saldo monetario) a 30 días / 15% respectivamente | Job diario | Notificación a Logística |

---

## 6. Catálogo de pantallas (14 mínimas + dashboard + 6 de multialmacén + 4 de dosificación nutricional)

Cada pantalla de listado incluye: filtros avanzados (fecha, estado, **almacén, sede, comedor**, proveedor, producto), buscador, exportación Excel/PDF, columna de estado con semáforo de color, y acceso al historial/auditoría del registro mediante ícono de "línea de tiempo". El filtro de almacén respeta siempre la regla RN-20 de alcance por usuario.

1. **Dashboard ejecutivo** — KPIs: stock crítico, contratos por vencer, OC pendientes, entregas observadas, pagos retenidos, consumo mensual, valorización de inventario. Selector de almacén/sede/comedor para ver consolidado o detalle.
2. **Planificación anual** (raciones, menús, BOM) — vista de calendario quincenal + tabla BOM calculada.
3. **Requerimiento anual de insumos** — tabla consolidada con estado de versión y aprobación.
4. **Proveedores y contratos** — ficha de proveedor + línea de tiempo de contratos.
5. **Productos contratados** — tabla con precio, tope físico, tope monetario, saldo físico, saldo monetario, barra de progreso de consumo.
6. **Órdenes de compra mensuales** — formulario con validación de saldo en tiempo real.
7. **Pedidos semanales/dosificados** — vista calendario semanal ligada al menú.
8. **Guías de remisión** — tabla con estado (pendiente/parcial/conforme/observado).
9. **Inspección y actas de observación** — formulario de inspección por línea + generador de acta con adjuntos de evidencia.
10. **Ingresos, kardex valorizado y bin card** — vista dual: kardex (columnas de valorización) y bin card (columnas físicas por ubicación).
11. **Solicitudes de cocina y notas de salida** — formulario de solicitud + validación de stock en vivo.
12. **Seguimiento guías vs. órdenes de compra** — tablero tipo kanban por estado.
13. **Conformidad, retenciones, penalidades e informes de pago** — generador de informe con checklist de actas pendientes.
14. **Reportes y auditoría** — generador de reportes parametrizables + bitácora inalterable.

15–20. **Multialmacén** — ver detalle completo en la sección 4.6.9 (maestro de almacenes, dashboard con filtro, distribución de OC por almacén, transferencias, ajustes/mermas/devoluciones/inventario físico, alertas por almacén).

21–24. **Dosificación nutricional** — ver detalle completo en 4.1A (catálogo nutricional, recetas/preparaciones, editor de receta con cálculo en vivo, dosificación y BOM por periodo).

Ver wireframes interactivos en el archivo adjunto `wireframes_pantallas_clave.html`.

---

## 7. Trazabilidad — vista lógica

Cada entidad "hoja" (kardex, bin card, informe de pago) mantiene claves foráneas hacia toda la cadena, permitiendo reconstruir, para cualquier `producto + fecha`, la ruta completa:

```
requerimiento_anual → contrato → producto_contratado → orden_compra →
orden_compra_detalle → pedido_semanal → guia_remision → guia_remision_detalle →
inspeccion_detalle → (acta_observacion) → ingreso_almacen → kardex_movimiento →
nota_salida → nota_salida_detalle → informe_conformidad_pago
```

Ver modelo relacional completo (multialmacén + dosificación nutricional) en `02_modelo_base_datos_v4_mysql.sql` (MySQL 8.0+) y diagrama en `03_diagrama_entidad_relacion_v3.mermaid`. v2 añadió `almacen_id` como dimensión de control local en cada entidad de stock/movimiento, manteniendo el contrato como control global (ver 4.6.2). v3 añade el catálogo nutricional versionado y las recetas como origen automático de la explosión de materiales, reemplazando la carga manual de `bom_detalle` por el cálculo derivado de `receta_ingrediente` (ver 4.1A). v4 porta el modelo a MySQL: `AUTO_INCREMENT`, `DATETIME`, `JSON`, `DECIMAL`, columnas generadas `STORED` y disparadores (`TRIGGER`) que refuerzan reglas que MySQL no puede expresar con índices parciales o `CHECK` entre filas (versión vigente única por alimento, suma de distribución por almacén, stock disponible antes de despachar).
