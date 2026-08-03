-- ============================================================================
-- SIGA-UNMSM · Sistema Integral de Gestión de Almacén y Abastecimiento
-- Modelo de base de datos relacional v4 (MySQL 8.0+)
-- Convertido desde 02_modelo_base_datos_v3.sql (PostgreSQL). Incluye:
--   v2: soporte MULTIALMACÉN                    (marcas "-- [MULTIALMACÉN]")
--   v3: DOSIFICACIÓN NUTRICIONAL Y RECETAS       (marcas "-- [NUTRICION]")
--   v4: PORTADO A MYSQL                          (marcas "-- [MYSQL]")
--
-- REQUISITOS: MySQL 8.0.16 o superior (necesario para que se apliquen los
-- CHECK constraints; en versiones anteriores se aceptan mas se ignoran).
-- Motor: InnoDB en todas las tablas (soporta FK, transacciones, generated
-- columns STORED). Codificación: utf8mb4 para soporte completo de acentos,
-- eñes y símbolos.
--
-- CAMBIOS PRINCIPALES RESPECTO A LA VERSIÓN POSTGRESQL:
--   • SERIAL / BIGSERIAL           → INT/BIGINT AUTO_INCREMENT PRIMARY KEY
--   • JSONB                        → JSON
--   • NUMERIC(p,s)                 → DECIMAL(p,s)  (alias equivalente)
--   • TIMESTAMP ... DEFAULT now()  → DATETIME ... DEFAULT CURRENT_TIMESTAMP
--     (se usa DATETIME en vez de TIMESTAMP para evitar el rango limitado a
--      2038 y el comportamiento de auto-actualización implícito de TIMESTAMP)
--   • concatenación con ||         → CONCAT_WS()
--   • índice parcial (WHERE ...)   → índice compuesto + regla aplicada por
--     trigger o en la capa de aplicación (MySQL no soporta índices parciales)
--   • claves foráneas EXPLÍCITAS   → CONSTRAINT ... FOREIGN KEY (col)
--     REFERENCES tabla(col). CORRECCIÓN IMPORTANTE: a diferencia de
--     PostgreSQL, MySQL analiza pero IGNORA una cláusula "REFERENCES" escrita
--     en línea dentro de la definición de columna (col INT REFERENCES t(c));
--     no crea ninguna restricción real, por eso Workbench mostraba las tablas
--     sin relaciones al hacer Reverse Engineer. Aquí cada FK se declara con
--     una cláusula CONSTRAINT ... FOREIGN KEY ... a nivel de tabla, que sí
--     genera la restricción y el índice, y que MySQL Workbench sí reconoce
--     y dibuja como relación en el diagrama EER.
-- ============================================================================

-- [MYSQL] Creación de base de datos y configuración regional
CREATE DATABASE IF NOT EXISTS siga_unmsm
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE siga_unmsm;

SET default_storage_engine = InnoDB;

-- [MYSQL] Desactiva la verificación de claves foráneas SOLO durante la
-- creación de tablas. Esto es la práctica estándar (la misma que usa
-- mysqldump) para que el script no falle por orden de ejecución si Workbench
-- corre las sentencias una por una, si se re-ejecuta parcialmente, o si en el
-- futuro se agregan referencias cruzadas entre tablas. Se reactiva más abajo,
-- antes de crear los índices, para que el resto del script (datos, triggers,
-- uso normal de la base) sí valide las relaciones.
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 0. SEGURIDAD Y ADMINISTRACIÓN
-- ============================================================
CREATE TABLE usuario (
    usuario_id          INT AUTO_INCREMENT PRIMARY KEY,
    nombres             VARCHAR(150) NOT NULL,
    apellidos           VARCHAR(150) NOT NULL,
    correo              VARCHAR(150) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL, -- [BACKEND] hash bcrypt, nunca texto plano
    rol_id              INT NOT NULL,
    sede_id             INT,
    estado              VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    creado_en           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rol (
    rol_id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(80) NOT NULL UNIQUE, -- ADMIN, NUTRICION, LOGISTICA_CENTRAL, ALMACENERO,
                                                       -- INSPECTOR, COCINA, PAGOS, PROVEEDOR
    acceso_todos_almacenes BOOLEAN NOT NULL DEFAULT false, -- [MULTIALMACÉN] true para ADMIN y LOGISTICA_CENTRAL
    descripcion         VARCHAR(255)
);

CREATE TABLE sede (
    sede_id             INT AUTO_INCREMENT PRIMARY KEY,
    nombre              VARCHAR(150) NOT NULL,
    direccion           VARCHAR(255)
);

-- [MULTIALMACÉN] Maestro de almacenes
CREATE TABLE almacen (
    almacen_id           INT AUTO_INCREMENT PRIMARY KEY,
    codigo                  VARCHAR(20) UNIQUE NOT NULL,  -- ALM-CU, ALM-CAN, ALM-VET, ALM-ADM
    nombre                    VARCHAR(200) NOT NULL,
    sede_id                     INT NOT NULL,
    direccion                     VARCHAR(255),
    tipo_comedor                    VARCHAR(60) NOT NULL, -- ESTUDIANTES, ADMINISTRATIVOS_DOCENTES
    responsable_id                    INT NOT NULL,
    estado                              VARCHAR(20) NOT NULL DEFAULT 'ACTIVO', -- ACTIVO, INACTIVO
    creado_en                             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_almacen_sede_id FOREIGN KEY (sede_id) REFERENCES sede(sede_id),
    CONSTRAINT fk_almacen_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

-- [MULTIALMACÉN] Ubicaciones internas por almacén: zona > estante > nivel > contenedor/cámara
CREATE TABLE ubicacion_interna (
    ubicacion_id           INT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                INT NOT NULL,
    zona                         VARCHAR(60) NOT NULL,
    estante                       VARCHAR(60),
    nivel                          VARCHAR(60),
    contenedor_camara                VARCHAR(60),
    es_cadena_frio                     BOOLEAN NOT NULL DEFAULT false,
    codigo_ubicacion                     VARCHAR(80) GENERATED ALWAYS AS
        (CONCAT_WS('-', zona, estante, nivel, contenedor_camara)) STORED,
    UNIQUE (almacen_id, zona, estante, nivel, contenedor_camara),
    CONSTRAINT fk_ubicacion_interna_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id)
);

-- [MULTIALMACÉN] Alcance de acceso de usuarios operativos a almacenes (RN-20)
CREATE TABLE usuario_almacen_acceso (
    usuario_id             INT NOT NULL,
    almacen_id                INT NOT NULL,
    PRIMARY KEY (usuario_id, almacen_id),
    CONSTRAINT fk_usuario_almacen_acceso_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id),
    CONSTRAINT fk_usuario_almacen_acceso_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id)
);

-- [MULTIALMACÉN] Cada comedor/centro de consumo pertenece a un único almacén
CREATE TABLE centro_consumo (
    centro_consumo_id   INT AUTO_INCREMENT PRIMARY KEY,
    sede_id             INT NOT NULL,
    almacen_id           INT NOT NULL, -- [MULTIALMACÉN]
    nombre                VARCHAR(150) NOT NULL,
    poblacion_referencia    INT,
    CONSTRAINT fk_centro_consumo_sede_id FOREIGN KEY (sede_id) REFERENCES sede(sede_id),
    CONSTRAINT fk_centro_consumo_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id)
);

CREATE TABLE auditoria_log (
    auditoria_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    entidad             VARCHAR(80) NOT NULL,
    entidad_id          BIGINT NOT NULL,
    accion              VARCHAR(40) NOT NULL,
    usuario_id          INT NOT NULL,
    detalle_json        JSON,
    creado_en           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_auditoria_log_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE adjunto (
    adjunto_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    entidad              VARCHAR(80) NOT NULL,
    entidad_id           BIGINT NOT NULL,
    nombre_archivo        VARCHAR(255) NOT NULL,
    url_almacenamiento    VARCHAR(500) NOT NULL,
    subido_por_id          INT NOT NULL,
    subido_en              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_adjunto_subido_por_id FOREIGN KEY (subido_por_id) REFERENCES usuario(usuario_id)
);

-- ============================================================
-- 1. CATÁLOGOS MAESTROS
-- ============================================================
CREATE TABLE unidad_medida (
    unidad_id           INT AUTO_INCREMENT PRIMARY KEY,
    codigo               VARCHAR(10) UNIQUE NOT NULL,
    nombre                VARCHAR(60) NOT NULL
);

-- ============================================================
-- 1A. [NUTRICION] CATÁLOGO NUTRICIONAL (Tabla Peruana de Composición de Alimentos)
-- ============================================================
CREATE TABLE categoria_alimento (
    categoria_alimento_id   INT AUTO_INCREMENT PRIMARY KEY,
    nombre                     VARCHAR(100) NOT NULL UNIQUE -- ej. Cereales, Lácteos, Carnes, Menestras...
);

-- Identidad estable del alimento (no cambia entre versiones)
CREATE TABLE alimento (
    alimento_id              INT AUTO_INCREMENT PRIMARY KEY,
    codigo                      VARCHAR(30) UNIQUE NOT NULL, -- código de la Tabla Peruana o institucional
    nombre                        VARCHAR(200) NOT NULL,
    categoria_alimento_id            INT NOT NULL,
    tipo                                VARCHAR(30) NOT NULL,
        -- BASE_TABLA, PREPARADO_IMPORTADO, PREPARACION_INSTITUCIONAL
    estado                                VARCHAR(20) NOT NULL DEFAULT 'ACTIVO', -- ACTIVO, INACTIVO (nunca se borra)
    creado_por_id                           INT,
    creado_en                                 DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alimento_categoria_alimento_id FOREIGN KEY (categoria_alimento_id) REFERENCES categoria_alimento(categoria_alimento_id),
    CONSTRAINT fk_alimento_creado_por_id FOREIGN KEY (creado_por_id) REFERENCES usuario(usuario_id)
);

-- Versión de valores nutricionales por 100 g — histórico inmutable, insert-only
CREATE TABLE alimento_version (
    alimento_version_id       INT AUTO_INCREMENT PRIMARY KEY,
    alimento_id                  INT NOT NULL,
    version                         INT NOT NULL,
    fuente                            VARCHAR(255) NOT NULL, -- ej. 'Tabla Peruana de Composición de Alimentos 2017'
    fecha_importacion                   DATE NOT NULL,
    vigente                                BOOLEAN NOT NULL DEFAULT true,
    -- valores nutricionales por 100 g
    energia_kcal                             DECIMAL(10,2),
    energia_kj                                 DECIMAL(10,2),
    agua_g                                       DECIMAL(10,3),
    proteinas_g                                    DECIMAL(10,3),
    grasa_total_g                                    DECIMAL(10,3),
    carbohidratos_totales_g                            DECIMAL(10,3),
    carbohidratos_disponibles_g                          DECIMAL(10,3),
    fibra_dietaria_g                                       DECIMAL(10,3),
    cenizas_g                                                DECIMAL(10,3),
    calcio_mg                                                  DECIMAL(10,3),
    fosforo_mg                                                   DECIMAL(10,3),
    zinc_mg                                                        DECIMAL(10,3),
    hierro_mg                                                        DECIMAL(10,3),
    vitamina_a_ug                                                      DECIMAL(10,3),
    tiamina_mg                                                           DECIMAL(10,3),
    riboflavina_mg                                                         DECIMAL(10,3),
    niacina_mg                                                               DECIMAL(10,3),
    vitamina_c_mg                                                              DECIMAL(10,3),
    acido_folico_ug                                                              DECIMAL(10,3),
    sodio_mg                                                                       DECIMAL(10,3),
    potasio_mg                                                                       DECIMAL(10,3),
    editado_por_id                                                                     INT,
    creado_en                                                                            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- [MYSQL] Refuerza "máx. 1 versión vigente por alimento" con una columna
    -- generada + índice único, en vez de un trigger que se auto-modifica
    -- (un BEFORE/AFTER INSERT trigger no puede hacer UPDATE de la misma
    -- tabla que lo disparó: MySQL lo rechaza con Error 1442). Esta columna
    -- vale alimento_id cuando vigente=1, y NULL cuando vigente=0; MySQL
    -- permite múltiples NULL en un índice único, así que solo bloquea el
    -- caso real: dos filas vigente=1 para el mismo alimento_id.
    vigente_key                                                                            INT GENERATED ALWAYS AS (IF(vigente, alimento_id, NULL)) STORED,
    UNIQUE (alimento_id, version),
    UNIQUE (vigente_key),
    CONSTRAINT fk_alimento_version_alimento_id FOREIGN KEY (alimento_id) REFERENCES alimento(alimento_id),
    CONSTRAINT fk_alimento_version_editado_por_id FOREIGN KEY (editado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE producto (
    producto_id          INT AUTO_INCREMENT PRIMARY KEY,
    codigo                VARCHAR(30) UNIQUE NOT NULL,
    nombre                 VARCHAR(200) NOT NULL,
    categoria               VARCHAR(80),
    unidad_id                INT NOT NULL,
    alimento_id                INT, -- [NUTRICION] vínculo con catálogo nutricional
    perecible                 BOOLEAN NOT NULL DEFAULT false,
    dias_vida_util               INT, -- para alertas de vencimiento por almacén
    stock_minimo_referencial        DECIMAL(14,4), -- default sugerido; cada almacén puede sobre-escribirlo
    estado                            VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    CONSTRAINT fk_producto_unidad_id FOREIGN KEY (unidad_id) REFERENCES unidad_medida(unidad_id),
    CONSTRAINT fk_producto_alimento_id FOREIGN KEY (alimento_id) REFERENCES alimento(alimento_id)
);

-- [MULTIALMACÉN] Parámetro de stock mínimo específico por almacén (puede diferir del referencial)
CREATE TABLE almacen_producto_parametro (
    almacen_id             INT NOT NULL,
    producto_id               INT NOT NULL,
    stock_minimo                 DECIMAL(14,4) NOT NULL,
    PRIMARY KEY (almacen_id, producto_id),
    CONSTRAINT fk_almacen_producto_parametro_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_almacen_producto_parametro_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

-- ============================================================
-- 2. MÓDULO 1 · PLANIFICACIÓN ESTRATÉGICA ANUAL
-- ============================================================
CREATE TABLE racion_anual (
    racion_anual_id       INT AUTO_INCREMENT PRIMARY KEY,
    sede_id                INT NOT NULL,
    centro_consumo_id       INT NOT NULL,
    anio                     INT NOT NULL,
    poblacion_atendida        INT NOT NULL,
    raciones_dia               INT NOT NULL,
    estado                      VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
    creado_por_id                INT NOT NULL,
    creado_en                     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_racion_anual_sede_id FOREIGN KEY (sede_id) REFERENCES sede(sede_id),
    CONSTRAINT fk_racion_anual_centro_consumo_id FOREIGN KEY (centro_consumo_id) REFERENCES centro_consumo(centro_consumo_id),
    CONSTRAINT fk_racion_anual_creado_por_id FOREIGN KEY (creado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE menu_quincenal (
    menu_id                INT AUTO_INCREMENT PRIMARY KEY,
    racion_anual_id          INT NOT NULL,
    quincena_inicio           DATE NOT NULL,
    quincena_fin                DATE NOT NULL,
    version                       INT NOT NULL DEFAULT 1,
    estado                         VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
    aprobado_por_id                 INT,
    aprobado_en                      DATETIME,
    creado_en                         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_menu_quincenal_racion_anual_id FOREIGN KEY (racion_anual_id) REFERENCES racion_anual(racion_anual_id),
    CONSTRAINT fk_menu_quincenal_aprobado_por_id FOREIGN KEY (aprobado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE menu_dia (
    menu_dia_id             INT AUTO_INCREMENT PRIMARY KEY,
    menu_id                   INT NOT NULL,
    fecha                       DATE NOT NULL,
    tipo_servicio                 VARCHAR(30) NOT NULL,
    raciones_programadas           INT NOT NULL,
    CONSTRAINT fk_menu_dia_menu_id FOREIGN KEY (menu_id) REFERENCES menu_quincenal(menu_id)
);

-- [NUTRICION] Preparación / receta institucional (identidad estable, versionable)
CREATE TABLE receta (
    receta_id                 INT AUTO_INCREMENT PRIMARY KEY,
    codigo                        VARCHAR(30) NOT NULL, -- [FIX] único junto con version, no solo
    nombre                          VARCHAR(200) NOT NULL,
    categoria_preparacion             VARCHAR(30) NOT NULL, -- SOPA, SEGUNDO, ENTRADA, BEBIDA, POSTRE
    descripcion                          TEXT,
    numero_raciones_base                   INT NOT NULL CHECK (numero_raciones_base > 0),
    tamano_porcion_g                         DECIMAL(10,2) NOT NULL CHECK (tamano_porcion_g > 0),
    rendimiento_pct                            DECIMAL(5,2) NOT NULL CHECK (rendimiento_pct > 0), -- RN-23
    merma_estimada_pct                           DECIMAL(5,2) NOT NULL DEFAULT 0,
    procedimiento                                  TEXT,
    version                                          INT NOT NULL DEFAULT 1,
    receta_padre_id                                    INT, -- [NUTRICION] versionamiento (RN-25)
    estado                                               VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
        -- BORRADOR, EN_REVISION, APROBADO, VIGENTE, DESCONTINUADO
    creado_por_id                                          INT NOT NULL,
    aprobado_por_id                                          INT,
    aprobado_en                                                DATETIME,
    creado_en                                                    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_receta_receta_padre_id FOREIGN KEY (receta_padre_id) REFERENCES receta(receta_id),
    CONSTRAINT fk_receta_creado_por_id FOREIGN KEY (creado_por_id) REFERENCES usuario(usuario_id),
    UNIQUE (codigo, version), -- [FIX] RN-25: cada version es una fila con el mismo codigo
    CONSTRAINT fk_receta_aprobado_por_id FOREIGN KEY (aprobado_por_id) REFERENCES usuario(usuario_id)
);

-- [NUTRICION] Ingredientes de la receta (referencian el catálogo nutricional)
CREATE TABLE receta_ingrediente (
    receta_ingrediente_id       INT AUTO_INCREMENT PRIMARY KEY,
    receta_id                      INT NOT NULL,
    alimento_id                      INT NOT NULL,
    cantidad_bruta_g                   DECIMAL(12,4) NOT NULL CHECK (cantidad_bruta_g > 0),
    cantidad_neta_g                      DECIMAL(12,4) NOT NULL CHECK (cantidad_neta_g > 0),
    unidad_id                              INT NOT NULL,
    factor_conversion                        DECIMAL(10,4) NOT NULL DEFAULT 1,
    merma_pct                                  DECIMAL(5,2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_receta_ingrediente_receta_id FOREIGN KEY (receta_id) REFERENCES receta(receta_id),
    CONSTRAINT fk_receta_ingrediente_alimento_id FOREIGN KEY (alimento_id) REFERENCES alimento(alimento_id),
    CONSTRAINT fk_receta_ingrediente_unidad_id FOREIGN KEY (unidad_id) REFERENCES unidad_medida(unidad_id)
);

-- [NUTRICION] Aporte nutricional calculado (cacheado) — total de la receta y por ración
CREATE TABLE receta_valor_nutricional (
    receta_id                    INT PRIMARY KEY,
    -- total de la receta completa (numero_raciones_base raciones)
    energia_kcal_total               DECIMAL(10,2), proteinas_g_total DECIMAL(10,3), grasa_total_g_total DECIMAL(10,3),
    carbohidratos_g_total              DECIMAL(10,3), fibra_g_total DECIMAL(10,3), sodio_mg_total DECIMAL(10,3),
    -- por ración = total / numero_raciones_base
    energia_kcal_racion                  DECIMAL(10,2), proteinas_g_racion DECIMAL(10,3), grasa_total_g_racion DECIMAL(10,3),
    carbohidratos_g_racion                 DECIMAL(10,3), fibra_g_racion DECIMAL(10,3), sodio_mg_racion DECIMAL(10,3),
    vitaminas_minerales_racion_json          JSON, -- resto de micronutrientes por ración
    recalculado_en                             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_receta_valor_nutricional_receta_id FOREIGN KEY (receta_id) REFERENCES receta(receta_id)
);

-- Plato programado en el menú del día — referencia una versión VIGENTE de receta (RN-22)
CREATE TABLE plato (
    plato_id                 INT AUTO_INCREMENT PRIMARY KEY,
    menu_dia_id                INT NOT NULL,
    receta_id                    INT NOT NULL, -- [NUTRICION] debe estar VIGENTE
    raciones_override              INT, -- opcional: sobre-escribe raciones_programadas del menu_dia para este plato
    CONSTRAINT fk_plato_menu_dia_id FOREIGN KEY (menu_dia_id) REFERENCES menu_dia(menu_dia_id),
    CONSTRAINT fk_plato_receta_id FOREIGN KEY (receta_id) REFERENCES receta(receta_id)
);

-- [NUTRICION] Dosificación calculada: requerimiento de cada ingrediente por
-- receta × día × comedor × almacén (sustituye a bom_detalle manual)
CREATE TABLE dosificacion_detalle (
    dosificacion_id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    menu_dia_id                    INT NOT NULL,
    plato_id                         INT NOT NULL,
    receta_id                          INT NOT NULL,
    centro_consumo_id                    INT NOT NULL,
    almacen_id                             INT NOT NULL,
    alimento_id                              INT NOT NULL,
    raciones_programadas                       INT NOT NULL,
    cantidad_bruta_requerida                     DECIMAL(14,4) NOT NULL, -- RN-24
    cantidad_neta_requerida                        DECIMAL(14,4) NOT NULL,
    calculado_en                                     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dosificacion_detalle_menu_dia_id FOREIGN KEY (menu_dia_id) REFERENCES menu_dia(menu_dia_id),
    CONSTRAINT fk_dosificacion_detalle_plato_id FOREIGN KEY (plato_id) REFERENCES plato(plato_id),
    CONSTRAINT fk_dosificacion_detalle_receta_id FOREIGN KEY (receta_id) REFERENCES receta(receta_id),
    CONSTRAINT fk_dosificacion_detalle_centro_consumo_id FOREIGN KEY (centro_consumo_id) REFERENCES centro_consumo(centro_consumo_id),
    CONSTRAINT fk_dosificacion_detalle_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_dosificacion_detalle_alimento_id FOREIGN KEY (alimento_id) REFERENCES alimento(alimento_id)
);

-- [NUTRICION] Explosión de materiales consolidada por periodo y almacén
CREATE TABLE bom_consolidado (
    bom_consolidado_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    tipo_periodo                    VARCHAR(20) NOT NULL, -- SEMANA, QUINCENA, MES, ANIO
    periodo_inicio                    DATE NOT NULL,
    periodo_fin                         DATE NOT NULL,
    almacen_id                            INT NOT NULL,
    producto_id                             INT NOT NULL,
    cantidad_requerida_total                  DECIMAL(14,4) NOT NULL,
    stock_disponible_referencia                 DECIMAL(14,4), -- foto al momento de generar (RN-28)
    saldo_contractual_referencia                  DECIMAL(14,4),
    estado_suficiencia                              VARCHAR(20), -- SUFICIENTE, ALERTA_STOCK, ALERTA_CONTRATO
    generado_en                                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bom_consolidado_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_bom_consolidado_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

CREATE TABLE requerimiento_anual (
    requerimiento_anual_id      INT AUTO_INCREMENT PRIMARY KEY,
    racion_anual_id                INT NOT NULL,
    version                          INT NOT NULL DEFAULT 1,
    estado                            VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
    presupuesto_referencial_total       DECIMAL(14,2),
    aprobado_por_id                       INT,
    aprobado_en                            DATETIME,
    creado_en                               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_requerimiento_anual_racion_anual_id FOREIGN KEY (racion_anual_id) REFERENCES racion_anual(racion_anual_id),
    CONSTRAINT fk_requerimiento_anual_aprobado_por_id FOREIGN KEY (aprobado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE requerimiento_anual_detalle (
    requerimiento_detalle_id     INT AUTO_INCREMENT PRIMARY KEY,
    requerimiento_anual_id          INT NOT NULL,
    producto_id                       INT NOT NULL,
    cantidad_estimada_anual              DECIMAL(14,4) NOT NULL,
    unidad_id                              INT NOT NULL,
    presupuesto_referencial                 DECIMAL(14,2),
    CONSTRAINT fk_requerimiento_anual_detalle_requerimiento_anual_id FOREIGN KEY (requerimiento_anual_id) REFERENCES requerimiento_anual(requerimiento_anual_id),
    CONSTRAINT fk_requerimiento_anual_detalle_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_requerimiento_anual_detalle_unidad_id FOREIGN KEY (unidad_id) REFERENCES unidad_medida(unidad_id)
);

-- ============================================================
-- 3. MÓDULO 2 · GESTIÓN CONTRACTUAL (control GLOBAL, no por almacén)
-- ============================================================
CREATE TABLE proveedor (
    proveedor_id             INT AUTO_INCREMENT PRIMARY KEY,
    ruc                         VARCHAR(11) UNIQUE NOT NULL,
    razon_social                  VARCHAR(200) NOT NULL,
    contacto_nombre                 VARCHAR(150),
    contacto_telefono                 VARCHAR(30),
    contacto_correo                     VARCHAR(150),
    estado                                VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    creado_en                              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contrato (
    contrato_id                INT AUTO_INCREMENT PRIMARY KEY,
    numero_contrato               VARCHAR(40) UNIQUE NOT NULL,
    proveedor_id                    INT NOT NULL,
    requerimiento_anual_id             INT NOT NULL,
    fecha_inicio                          DATE NOT NULL,
    fecha_fin                               DATE NOT NULL,
    presupuesto_total                         DECIMAL(14,2) NOT NULL,
    condiciones                                 TEXT,
    penalidad_json                                JSON,
    responsable_id                                  INT NOT NULL,
    estado                                            VARCHAR(20) NOT NULL DEFAULT 'VIGENTE',
    creado_en                                          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (fecha_fin > fecha_inicio),
    CONSTRAINT fk_contrato_proveedor_id FOREIGN KEY (proveedor_id) REFERENCES proveedor(proveedor_id),
    CONSTRAINT fk_contrato_requerimiento_anual_id FOREIGN KEY (requerimiento_anual_id) REFERENCES requerimiento_anual(requerimiento_anual_id),
    CONSTRAINT fk_contrato_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE cronograma_entrega (
    cronograma_id               INT AUTO_INCREMENT PRIMARY KEY,
    contrato_id                    INT NOT NULL,
    periodo                          VARCHAR(20) NOT NULL,
    fecha_programada                  DATE NOT NULL,
    CONSTRAINT fk_cronograma_entrega_contrato_id FOREIGN KEY (contrato_id) REFERENCES contrato(contrato_id)
);

-- Saldo físico/monetario GLOBAL del contrato (no distingue almacén, ver RN-19)
CREATE TABLE producto_contratado (
    producto_contratado_id         INT AUTO_INCREMENT PRIMARY KEY,
    contrato_id                       INT NOT NULL,
    producto_id                         INT NOT NULL,
    precio_unitario                       DECIMAL(12,4) NOT NULL CHECK (precio_unitario > 0),
    cantidad_contratada                     DECIMAL(14,4) NOT NULL CHECK (cantidad_contratada > 0),
    tope_monetario                            DECIMAL(14,2) GENERATED ALWAYS AS (precio_unitario * cantidad_contratada) STORED,
    saldo_fisico                                DECIMAL(14,4) NOT NULL,
    saldo_monetario                               DECIMAL(14,2) NOT NULL,
    UNIQUE (contrato_id, producto_id),
    CONSTRAINT fk_producto_contratado_contrato_id FOREIGN KEY (contrato_id) REFERENCES contrato(contrato_id),
    CONSTRAINT fk_producto_contratado_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

-- ============================================================
-- 4. MÓDULO 3 · CICLO MENSUAL DE COMPRA Y RECEPCIÓN
-- ============================================================
CREATE TABLE orden_compra (
    orden_compra_id               INT AUTO_INCREMENT PRIMARY KEY,
    numero_oc                        VARCHAR(40) UNIQUE NOT NULL,
    contrato_id                        INT NOT NULL,
    periodo_mes                          DATE NOT NULL,
    estado                                 VARCHAR(20) NOT NULL DEFAULT 'EMITIDA',
    responsable_id                           INT NOT NULL,
    creado_en                                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orden_compra_contrato_id FOREIGN KEY (contrato_id) REFERENCES contrato(contrato_id),
    CONSTRAINT fk_orden_compra_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE orden_compra_detalle (
    orden_compra_detalle_id         INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_id                    INT NOT NULL,
    producto_contratado_id                INT NOT NULL,
    cantidad_solicitada                      DECIMAL(14,4) NOT NULL CHECK (cantidad_solicitada > 0),
    precio_unitario_aplicado                   DECIMAL(12,4) NOT NULL,
    cantidad_ingresada_acumulada                 DECIMAL(14,4) NOT NULL DEFAULT 0,
    saldo_oc                                       DECIMAL(14,4) GENERATED ALWAYS AS (cantidad_solicitada - cantidad_ingresada_acumulada) STORED,
    CONSTRAINT fk_orden_compra_detalle_orden_compra_id FOREIGN KEY (orden_compra_id) REFERENCES orden_compra(orden_compra_id),
    CONSTRAINT fk_orden_compra_detalle_producto_contratado_id FOREIGN KEY (producto_contratado_id) REFERENCES producto_contratado(producto_contratado_id)
);

-- [MULTIALMACÉN] Distribución de cada línea de OC entre 1..N almacenes destino (RN-15)
CREATE TABLE orden_compra_distribucion (
    orden_compra_distribucion_id    INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_detalle_id            INT NOT NULL,
    almacen_id                           INT NOT NULL,
    cantidad_distribuida                   DECIMAL(14,4) NOT NULL CHECK (cantidad_distribuida > 0),
    UNIQUE (orden_compra_detalle_id, almacen_id),
    -- Regla de aplicación (a nivel de servicio/trigger):
    -- SUM(cantidad_distribuida) por orden_compra_detalle_id = cantidad_solicitada
    CONSTRAINT fk_orden_compra_distribucion_orden_compra_detalle_id FOREIGN KEY (orden_compra_detalle_id) REFERENCES orden_compra_detalle(orden_compra_detalle_id),
    CONSTRAINT fk_orden_compra_distribucion_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id)
);

-- [MULTIALMACÉN] Pedido semanal por sede + menú + almacén (RN-16)
CREATE TABLE pedido_semanal (
    pedido_semanal_id                INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_id                     INT NOT NULL,
    menu_id                                INT NOT NULL,
    almacen_id                               INT NOT NULL, -- [MULTIALMACÉN]
    semana_inicio                              DATE NOT NULL,
    semana_fin                                   DATE NOT NULL,
    estado                                         VARCHAR(20) NOT NULL DEFAULT 'PROGRAMADO',
    UNIQUE (menu_id, almacen_id, semana_inicio),
    CONSTRAINT fk_pedido_semanal_orden_compra_id FOREIGN KEY (orden_compra_id) REFERENCES orden_compra(orden_compra_id),
    CONSTRAINT fk_pedido_semanal_menu_id FOREIGN KEY (menu_id) REFERENCES menu_quincenal(menu_id),
    CONSTRAINT fk_pedido_semanal_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id)
);

-- [MULTIALMACÉN] Toda guía indica almacén de destino obligatorio (RN-13)
CREATE TABLE guia_remision (
    guia_remision_id                  INT AUTO_INCREMENT PRIMARY KEY,
    numero_guia                          VARCHAR(40) NOT NULL,
    proveedor_id                           INT NOT NULL,
    orden_compra_id                          INT NOT NULL,
    pedido_semanal_id                          INT NOT NULL,
    almacen_destino_id                           INT NOT NULL, -- [MULTIALMACÉN]
    fecha_entrega                                DATE NOT NULL,
    estado                                         VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    creado_en                                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (numero_guia, proveedor_id),
    CONSTRAINT fk_guia_remision_proveedor_id FOREIGN KEY (proveedor_id) REFERENCES proveedor(proveedor_id),
    CONSTRAINT fk_guia_remision_orden_compra_id FOREIGN KEY (orden_compra_id) REFERENCES orden_compra(orden_compra_id),
    CONSTRAINT fk_guia_remision_pedido_semanal_id FOREIGN KEY (pedido_semanal_id) REFERENCES pedido_semanal(pedido_semanal_id),
    CONSTRAINT fk_guia_remision_almacen_destino_id FOREIGN KEY (almacen_destino_id) REFERENCES almacen(almacen_id)
);

CREATE TABLE guia_remision_detalle (
    guia_remision_detalle_id           INT AUTO_INCREMENT PRIMARY KEY,
    guia_remision_id                      INT NOT NULL,
    orden_compra_detalle_id                 INT NOT NULL,
    cantidad_entregada                        DECIMAL(14,4) NOT NULL CHECK (cantidad_entregada > 0),
    lote                                        VARCHAR(60),
    fecha_vencimiento                             DATE, -- para alertas por almacén
    CONSTRAINT fk_guia_remision_detalle_guia_remision_id FOREIGN KEY (guia_remision_id) REFERENCES guia_remision(guia_remision_id),
    CONSTRAINT fk_guia_remision_detalle_orden_compra_detalle_id FOREIGN KEY (orden_compra_detalle_id) REFERENCES orden_compra_detalle(orden_compra_detalle_id)
);

CREATE TABLE inspeccion (
    inspeccion_id                        INT AUTO_INCREMENT PRIMARY KEY,
    guia_remision_id                        INT NOT NULL,
    inspector_id                              INT NOT NULL,
    fecha_inspeccion                            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_inspeccion_guia_remision_id FOREIGN KEY (guia_remision_id) REFERENCES guia_remision(guia_remision_id),
    CONSTRAINT fk_inspeccion_inspector_id FOREIGN KEY (inspector_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE inspeccion_detalle (
    inspeccion_detalle_id                 INT AUTO_INCREMENT PRIMARY KEY,
    inspeccion_id                            INT NOT NULL,
    guia_remision_detalle_id                    INT NOT NULL,
    cantidad_conforme                              DECIMAL(14,4) NOT NULL DEFAULT 0,
    cantidad_observada                               DECIMAL(14,4) NOT NULL DEFAULT 0,
    resultado                                          VARCHAR(20) NOT NULL,
    CHECK (cantidad_conforme + cantidad_observada > 0),
    CONSTRAINT fk_inspeccion_detalle_inspeccion_id FOREIGN KEY (inspeccion_id) REFERENCES inspeccion(inspeccion_id),
    CONSTRAINT fk_inspeccion_detalle_guia_remision_detalle_id FOREIGN KEY (guia_remision_detalle_id) REFERENCES guia_remision_detalle(guia_remision_detalle_id)
);

CREATE TABLE acta_observacion (
    acta_observacion_id                    INT AUTO_INCREMENT PRIMARY KEY,
    numero_acta                               VARCHAR(40) UNIQUE NOT NULL,
    inspeccion_detalle_id                       INT NOT NULL,
    motivo                                        VARCHAR(255) NOT NULL,
    cantidad_observada                              DECIMAL(14,4) NOT NULL,
    responsable_id                                    INT NOT NULL,
    plazo_subsanacion                                   DATE NOT NULL,
    estado                                                VARCHAR(20) NOT NULL DEFAULT 'ABIERTA',
    creado_en                                              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_acta_observacion_inspeccion_detalle_id FOREIGN KEY (inspeccion_detalle_id) REFERENCES inspeccion_detalle(inspeccion_detalle_id),
    CONSTRAINT fk_acta_observacion_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE subsanacion (
    subsanacion_id                          INT AUTO_INCREMENT PRIMARY KEY,
    acta_observacion_id                        INT NOT NULL,
    fecha_presentacion                            DATE NOT NULL,
    descripcion                                     TEXT,
    resultado_reinspeccion                            VARCHAR(20),
    inspector_id                                        INT,
    creado_en                                             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subsanacion_acta_observacion_id FOREIGN KEY (acta_observacion_id) REFERENCES acta_observacion(acta_observacion_id),
    CONSTRAINT fk_subsanacion_inspector_id FOREIGN KEY (inspector_id) REFERENCES usuario(usuario_id)
);

-- ============================================================
-- 5. ALMACÉN · INGRESOS, STOCK, KARDEX, BIN CARD (control LOCAL por almacén)
-- ============================================================
CREATE TABLE ingreso_almacen (
    ingreso_almacen_id                      INT AUTO_INCREMENT PRIMARY KEY,
    numero_ingreso                             VARCHAR(40) UNIQUE NOT NULL,
    guia_remision_id                             INT NOT NULL,
    almacen_id                                     INT NOT NULL, -- [MULTIALMACÉN] = guia.almacen_destino_id
    almacenero_id                                  INT NOT NULL,
    fecha_ingreso                                    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ingreso_almacen_guia_remision_id FOREIGN KEY (guia_remision_id) REFERENCES guia_remision(guia_remision_id),
    CONSTRAINT fk_ingreso_almacen_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_ingreso_almacen_almacenero_id FOREIGN KEY (almacenero_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE ingreso_almacen_detalle (
    ingreso_almacen_detalle_id                INT AUTO_INCREMENT PRIMARY KEY,
    ingreso_almacen_id                           INT NOT NULL,
    inspeccion_detalle_id                          INT NOT NULL,
    producto_id                                      INT NOT NULL,
    cantidad_ingresada                                 DECIMAL(14,4) NOT NULL CHECK (cantidad_ingresada > 0),
    costo_unitario                                       DECIMAL(12,4) NOT NULL,
    ubicacion_id                                           INT,
    CONSTRAINT fk_ingreso_almacen_detalle_ingreso_almacen_id FOREIGN KEY (ingreso_almacen_id) REFERENCES ingreso_almacen(ingreso_almacen_id),
    CONSTRAINT fk_ingreso_almacen_detalle_inspeccion_detalle_id FOREIGN KEY (inspeccion_detalle_id) REFERENCES inspeccion_detalle(inspeccion_detalle_id),
    CONSTRAINT fk_ingreso_almacen_detalle_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_ingreso_almacen_detalle_ubicacion_id FOREIGN KEY (ubicacion_id) REFERENCES ubicacion_interna(ubicacion_id)
);

-- [MULTIALMACÉN] Stock por (almacén, producto): físico, comprometido, disponible, valorizado
CREATE TABLE stock_almacen_producto (
    almacen_id                    INT NOT NULL,
    producto_id                      INT NOT NULL,
    stock_fisico                        DECIMAL(14,4) NOT NULL DEFAULT 0,
    stock_comprometido                     DECIMAL(14,4) NOT NULL DEFAULT 0,
    stock_disponible                          DECIMAL(14,4) GENERATED ALWAYS AS (stock_fisico - stock_comprometido) STORED,
    valor_promedio_unitario                      DECIMAL(12,4) NOT NULL DEFAULT 0,
    valor_valorizado                                DECIMAL(14,2) GENERATED ALWAYS AS (stock_fisico * valor_promedio_unitario) STORED,
    actualizado_en                                    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (almacen_id, producto_id),
    CONSTRAINT fk_stock_almacen_producto_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_stock_almacen_producto_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

-- Kardex valorizado — INSERT-ONLY, ahora con dimensión almacén (RN-06 + RN-14)
CREATE TABLE kardex_movimiento (
    kardex_id                        BIGINT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                          INT NOT NULL, -- [MULTIALMACÉN]
    producto_id                           INT NOT NULL,
    tipo_movimiento                         VARCHAR(30) NOT NULL,
        -- INGRESO, SALIDA, AJUSTE, MERMA, DEVOLUCION_PROVEEDOR, DEVOLUCION_COCINA,
        -- TRANSFERENCIA_SALIDA, TRANSFERENCIA_INGRESO, INVENTARIO_AJUSTE
    referencia_tipo                           VARCHAR(40) NOT NULL,
    referencia_id                               BIGINT NOT NULL,
    cantidad                                      DECIMAL(14,4) NOT NULL,
    costo_unitario                                  DECIMAL(12,4) NOT NULL,
    saldo_cantidad_resultante                         DECIMAL(14,4) NOT NULL,
    saldo_valorizado_resultante                         DECIMAL(14,2) NOT NULL,
    registrado_por_id                                     INT NOT NULL,
    creado_en                                               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_kardex_movimiento_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_kardex_movimiento_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_kardex_movimiento_registrado_por_id FOREIGN KEY (registrado_por_id) REFERENCES usuario(usuario_id)
);

-- Bin card físico — INSERT-ONLY, ligado a ubicación interna del almacén
CREATE TABLE bin_card_movimiento (
    bin_card_id                       BIGINT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                           INT NOT NULL, -- [MULTIALMACÉN]
    producto_id                             INT NOT NULL,
    ubicacion_id                               INT NOT NULL,
    tipo_movimiento                              VARCHAR(30) NOT NULL,
    referencia_tipo                                VARCHAR(40) NOT NULL,
    referencia_id                                    BIGINT NOT NULL,
    cantidad                                           DECIMAL(14,4) NOT NULL,
    saldo_fisico_resultante                              DECIMAL(14,4) NOT NULL,
    creado_en                                              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bin_card_movimiento_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_bin_card_movimiento_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_bin_card_movimiento_ubicacion_id FOREIGN KEY (ubicacion_id) REFERENCES ubicacion_interna(ubicacion_id)
);

-- [MULTIALMACÉN] Ajustes de inventario
CREATE TABLE ajuste_inventario (
    ajuste_id                          INT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                            INT NOT NULL,
    producto_id                             INT NOT NULL,
    cantidad_ajuste                           DECIMAL(14,4) NOT NULL, -- positivo o negativo
    motivo                                      VARCHAR(255) NOT NULL,
    responsable_id                                INT NOT NULL,
    creado_en                                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ajuste_inventario_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_ajuste_inventario_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_ajuste_inventario_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

-- [MULTIALMACÉN] Mermas
CREATE TABLE merma (
    merma_id                            INT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                             INT NOT NULL,
    producto_id                              INT NOT NULL,
    cantidad                                   DECIMAL(14,4) NOT NULL CHECK (cantidad > 0),
    motivo                                       VARCHAR(255) NOT NULL, -- VENCIMIENTO, DETERIORO, ROTURA...
    responsable_id                                 INT NOT NULL,
    creado_en                                        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_merma_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_merma_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_merma_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

-- [MULTIALMACÉN] Devoluciones (a proveedor o desde cocina)
CREATE TABLE devolucion (
    devolucion_id                        INT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                              INT NOT NULL,
    producto_id                               INT NOT NULL,
    tipo                                        VARCHAR(30) NOT NULL, -- A_PROVEEDOR, DESDE_COCINA
    cantidad                                      DECIMAL(14,4) NOT NULL CHECK (cantidad > 0),
    referencia_tipo                                 VARCHAR(40), -- 'guia_remision', 'nota_salida'
    referencia_id                                     BIGINT,
    motivo                                              VARCHAR(255),
    responsable_id                                        INT NOT NULL,
    creado_en                                               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_devolucion_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_devolucion_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_devolucion_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

-- [MULTIALMACÉN] Inventario físico periódico
CREATE TABLE inventario_fisico (
    inventario_fisico_id                  INT AUTO_INCREMENT PRIMARY KEY,
    almacen_id                               INT NOT NULL,
    fecha_conteo                               DATE NOT NULL,
    responsable_id                               INT NOT NULL,
    estado                                         VARCHAR(20) NOT NULL DEFAULT 'EN_PROCESO', -- EN_PROCESO, CERRADO
    CONSTRAINT fk_inventario_fisico_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_inventario_fisico_responsable_id FOREIGN KEY (responsable_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE inventario_fisico_detalle (
    inventario_fisico_detalle_id            INT AUTO_INCREMENT PRIMARY KEY,
    inventario_fisico_id                       INT NOT NULL,
    producto_id                                  INT NOT NULL,
    stock_sistema                                  DECIMAL(14,4) NOT NULL,
    stock_contado                                    DECIMAL(14,4) NOT NULL,
    diferencia                                         DECIMAL(14,4) GENERATED ALWAYS AS (stock_contado - stock_sistema) STORED,
    ajuste_generado_id                                   INT,
    CONSTRAINT fk_inventario_fisico_detalle_inventario_fisico_id FOREIGN KEY (inventario_fisico_id) REFERENCES inventario_fisico(inventario_fisico_id),
    CONSTRAINT fk_inventario_fisico_detalle_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id),
    CONSTRAINT fk_inventario_fisico_detalle_ajuste_generado_id FOREIGN KEY (ajuste_generado_id) REFERENCES ajuste_inventario(ajuste_id)
);

-- [MULTIALMACÉN] Transferencias entre almacenes
CREATE TABLE transferencia_almacen (
    transferencia_id                        INT AUTO_INCREMENT PRIMARY KEY,
    numero_transferencia                       VARCHAR(40) UNIQUE NOT NULL,
    almacen_origen_id                            INT NOT NULL,
    almacen_destino_id                             INT NOT NULL,
    responsable_origen_id                            INT NOT NULL,
    responsable_destino_id                             INT,
    fecha_salida                                         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_recepcion                                        DATETIME,
    estado                                                   VARCHAR(30) NOT NULL DEFAULT 'EN_TRANSITO',
        -- EN_TRANSITO, RECIBIDA_CONFORME, RECIBIDA_CON_DIFERENCIA, ANULADA
    CHECK (almacen_origen_id <> almacen_destino_id),
    CONSTRAINT fk_transferencia_almacen_almacen_origen_id FOREIGN KEY (almacen_origen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_transferencia_almacen_almacen_destino_id FOREIGN KEY (almacen_destino_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_transferencia_almacen_responsable_origen_id FOREIGN KEY (responsable_origen_id) REFERENCES usuario(usuario_id),
    CONSTRAINT fk_transferencia_almacen_responsable_destino_id FOREIGN KEY (responsable_destino_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE transferencia_almacen_detalle (
    transferencia_detalle_id                  INT AUTO_INCREMENT PRIMARY KEY,
    transferencia_id                             INT NOT NULL,
    producto_id                                    INT NOT NULL,
    cantidad_enviada                                 DECIMAL(14,4) NOT NULL CHECK (cantidad_enviada > 0),
    cantidad_recibida                                  DECIMAL(14,4),
    diferencia                                           DECIMAL(14,4) GENERATED ALWAYS AS (COALESCE(cantidad_recibida,0) - cantidad_enviada) STORED,
    observacion_diferencia                                 VARCHAR(255),
    CONSTRAINT fk_transferencia_almacen_detalle_transferencia_id FOREIGN KEY (transferencia_id) REFERENCES transferencia_almacen(transferencia_id),
    CONSTRAINT fk_transferencia_almacen_detalle_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

-- ============================================================
-- 6. MÓDULO 4 · COCINA Y CONSUMO (alcance LOCAL, RN-17)
-- ============================================================
CREATE TABLE solicitud_cocina (
    solicitud_cocina_id                INT AUTO_INCREMENT PRIMARY KEY,
    numero_solicitud                      VARCHAR(40) UNIQUE NOT NULL,
    centro_consumo_id                       INT NOT NULL,
    almacen_id                                INT NOT NULL, -- [MULTIALMACÉN] = centro_consumo.almacen_id
    menu_dia_id                                 INT NOT NULL,
    solicitado_por_id                             INT NOT NULL,
    estado                                          VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    creado_en                                         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_solicitud_cocina_centro_consumo_id FOREIGN KEY (centro_consumo_id) REFERENCES centro_consumo(centro_consumo_id),
    CONSTRAINT fk_solicitud_cocina_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_solicitud_cocina_menu_dia_id FOREIGN KEY (menu_dia_id) REFERENCES menu_dia(menu_dia_id),
    CONSTRAINT fk_solicitud_cocina_solicitado_por_id FOREIGN KEY (solicitado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE solicitud_cocina_detalle (
    solicitud_cocina_detalle_id           INT AUTO_INCREMENT PRIMARY KEY,
    solicitud_cocina_id                      INT NOT NULL,
    producto_id                                INT NOT NULL,
    cantidad_solicitada                          DECIMAL(14,4) NOT NULL CHECK (cantidad_solicitada > 0),
    cantidad_teorica_bom                           DECIMAL(14,4),
    CONSTRAINT fk_solicitud_cocina_detalle_solicitud_cocina_id FOREIGN KEY (solicitud_cocina_id) REFERENCES solicitud_cocina(solicitud_cocina_id),
    CONSTRAINT fk_solicitud_cocina_detalle_producto_id FOREIGN KEY (producto_id) REFERENCES producto(producto_id)
);

CREATE TABLE nota_salida (
    nota_salida_id                         INT AUTO_INCREMENT PRIMARY KEY,
    numero_nota                               VARCHAR(40) UNIQUE NOT NULL,
    solicitud_cocina_id                         INT NOT NULL,
    almacen_id                                    INT NOT NULL, -- [MULTIALMACÉN]
    almacenero_id                                   INT NOT NULL,
    fecha_salida                                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_nota_salida_solicitud_cocina_id FOREIGN KEY (solicitud_cocina_id) REFERENCES solicitud_cocina(solicitud_cocina_id),
    CONSTRAINT fk_nota_salida_almacen_id FOREIGN KEY (almacen_id) REFERENCES almacen(almacen_id),
    CONSTRAINT fk_nota_salida_almacenero_id FOREIGN KEY (almacenero_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE nota_salida_detalle (
    nota_salida_detalle_id                   INT AUTO_INCREMENT PRIMARY KEY,
    nota_salida_id                              INT NOT NULL,
    solicitud_cocina_detalle_id                   INT NOT NULL,
    cantidad_despachada                             DECIMAL(14,4) NOT NULL CHECK (cantidad_despachada > 0),
    costo_unitario                                    DECIMAL(12,4) NOT NULL,
    CONSTRAINT fk_nota_salida_detalle_nota_salida_id FOREIGN KEY (nota_salida_id) REFERENCES nota_salida(nota_salida_id),
    CONSTRAINT fk_nota_salida_detalle_solicitud_cocina_detalle_id FOREIGN KEY (solicitud_cocina_detalle_id) REFERENCES solicitud_cocina_detalle(solicitud_cocina_detalle_id)
);

-- ============================================================
-- 7. MÓDULO 5 · CONFORMIDAD Y PAGOS (control GLOBAL por contrato/OC)
-- ============================================================
CREATE TABLE penalidad (
    penalidad_id                          INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_id                          INT NOT NULL,
    acta_observacion_id                        INT,
    monto_penalidad                              DECIMAL(14,2) NOT NULL,
    motivo                                         VARCHAR(255) NOT NULL,
    creado_en                                        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_penalidad_orden_compra_id FOREIGN KEY (orden_compra_id) REFERENCES orden_compra(orden_compra_id),
    CONSTRAINT fk_penalidad_acta_observacion_id FOREIGN KEY (acta_observacion_id) REFERENCES acta_observacion(acta_observacion_id)
);

CREATE TABLE informe_conformidad_pago (
    informe_id                            INT AUTO_INCREMENT PRIMARY KEY,
    numero_informe                           VARCHAR(40) UNIQUE NOT NULL,
    orden_compra_id                            INT NOT NULL,
    monto_conforme_total                         DECIMAL(14,2) NOT NULL,
    monto_retenido_total                           DECIMAL(14,2) NOT NULL DEFAULT 0,
    monto_penalidad_total                            DECIMAL(14,2) NOT NULL DEFAULT 0,
    generado_por_id                                    INT NOT NULL,
    estado                                               VARCHAR(20) NOT NULL DEFAULT 'ENVIADO',
    fecha_envio                                            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_pago                                               DATETIME,
    CONSTRAINT fk_informe_conformidad_pago_orden_compra_id FOREIGN KEY (orden_compra_id) REFERENCES orden_compra(orden_compra_id),
    CONSTRAINT fk_informe_conformidad_pago_generado_por_id FOREIGN KEY (generado_por_id) REFERENCES usuario(usuario_id)
);

CREATE TABLE informe_conformidad_detalle (
    informe_detalle_id                     INT AUTO_INCREMENT PRIMARY KEY,
    informe_id                                INT NOT NULL,
    orden_compra_detalle_id                     INT NOT NULL,
    cantidad_conforme                             DECIMAL(14,4) NOT NULL,
    monto_conforme                                  DECIMAL(14,2) NOT NULL,
    cantidad_retenida                                 DECIMAL(14,4) NOT NULL DEFAULT 0,
    monto_retenido                                      DECIMAL(14,2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_informe_conformidad_detalle_informe_id FOREIGN KEY (informe_id) REFERENCES informe_conformidad_pago(informe_id),
    CONSTRAINT fk_informe_conformidad_detalle_orden_compra_detalle_id FOREIGN KEY (orden_compra_detalle_id) REFERENCES orden_compra_detalle(orden_compra_detalle_id)
);

-- ============================================================
-- 8. AUTORIZACIONES DE EXCEDENTE (RN-03)
-- ============================================================
CREATE TABLE autorizacion_excedente (
    autorizacion_excedente_id             INT AUTO_INCREMENT PRIMARY KEY,
    orden_compra_detalle_id                  INT NOT NULL,
    cantidad_excedente                         DECIMAL(14,4) NOT NULL,
    justificacion                                TEXT NOT NULL,
    autorizado_por_id                              INT NOT NULL,
    creado_en                                        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_autorizacion_excedente_orden_compra_detalle_id FOREIGN KEY (orden_compra_detalle_id) REFERENCES orden_compra_detalle(orden_compra_detalle_id),
    CONSTRAINT fk_autorizacion_excedente_autorizado_por_id FOREIGN KEY (autorizado_por_id) REFERENCES usuario(usuario_id)
);

-- [MYSQL] Reactiva la verificación de claves foráneas: todas las tablas ya
-- existen, así que de aquí en adelante (índices, datos, triggers, y
-- cualquier INSERT/UPDATE/DELETE futuro) las relaciones sí se validan.
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- ÍNDICES CLAVE (incluye dimensión almacén para consultas locales/consolidadas)
-- ============================================================
CREATE INDEX idx_oc_contrato ON orden_compra(contrato_id);
CREATE INDEX idx_ocd_oc ON orden_compra_detalle(orden_compra_id);
CREATE INDEX idx_ocdistrib_almacen ON orden_compra_distribucion(almacen_id);
CREATE INDEX idx_guia_oc ON guia_remision(orden_compra_id);
CREATE INDEX idx_guia_pedido ON guia_remision(pedido_semanal_id);
CREATE INDEX idx_guia_almacen ON guia_remision(almacen_destino_id);
CREATE INDEX idx_kardex_almacen_producto_fecha ON kardex_movimiento(almacen_id, producto_id, creado_en);
CREATE INDEX idx_bincard_almacen_producto ON bin_card_movimiento(almacen_id, producto_id);
CREATE INDEX idx_stock_almacen ON stock_almacen_producto(almacen_id);
CREATE INDEX idx_transferencia_origen ON transferencia_almacen(almacen_origen_id);
CREATE INDEX idx_transferencia_destino ON transferencia_almacen(almacen_destino_id);
CREATE INDEX idx_solicitud_almacen ON solicitud_cocina(almacen_id);
CREATE INDEX idx_acta_estado ON acta_observacion(estado);
CREATE INDEX idx_informe_oc ON informe_conformidad_pago(orden_compra_id);
CREATE INDEX idx_auditoria_entidad ON auditoria_log(entidad, entidad_id);

-- [NUTRICION]
CREATE INDEX idx_alimento_version_vigente ON alimento_version(alimento_id, vigente);
-- Nota MySQL: la restricción real "máx. 1 vigente=true por alimento_id" ya
-- queda garantizada por el índice único `vigente_key` (columna generada)
-- definido junto a la tabla alimento_version, no por un trigger (ver notas
-- en la sección de TRIGGERS más abajo). Este índice compuesto es solo para
-- acelerar las consultas filtradas por alimento_id + vigente.
CREATE INDEX idx_receta_estado ON receta(estado);
CREATE INDEX idx_receta_ingrediente_receta ON receta_ingrediente(receta_id);
CREATE INDEX idx_dosificacion_menu_dia ON dosificacion_detalle(menu_dia_id, almacen_id);
CREATE INDEX idx_dosificacion_alimento ON dosificacion_detalle(alimento_id);
CREATE INDEX idx_bom_consolidado_periodo ON bom_consolidado(tipo_periodo, periodo_inicio, almacen_id);

-- ============================================================
-- DATOS INICIALES · Maestro de almacenes (según especificación funcional)
-- ============================================================
-- INSERT INTO almacen (codigo, nombre, sede_id, tipo_comedor, responsable_id) VALUES
--   ('ALM-CU',  'Almacén Comedor de Alumnos – Ciudad Universitaria', 1, 'ESTUDIANTES', 1),
--   ('ALM-CAN', 'Almacén Comedor de Alumnos – Cangallo',              2, 'ESTUDIANTES', 1),
--   ('ALM-VET', 'Almacén Comedor de Alumnos – Veterinaria',           3, 'ESTUDIANTES', 1),
--   ('ALM-ADM', 'Almacén Comedor de Administrativos y Docentes',      1, 'ADMINISTRATIVOS_DOCENTES', 1);

-- ============================================================
-- [MYSQL] TRIGGERS · reglas que PostgreSQL resolvía con CHECK/lógica de
-- servicio y que en MySQL conviene reforzar a nivel de motor, ya que MySQL
-- no soporta índices/constraints parciales ni CHECK entre filas distintas.
--
-- NOTA: la regla "solo 1 versión vigente por alimento" NO se implementa
-- aquí como trigger porque MySQL prohíbe que un trigger modifique (UPDATE/
-- INSERT/DELETE) la MISMA tabla que lo disparó — lo rechaza con
-- Error 1442 ("Can't update table ... in stored function/trigger because
-- it is already used by statement which invoked this stored function/
-- trigger"). Esa regla ya queda garantizada por el índice único generado
-- `vigente_key` en la definición de `alimento_version` (ver arriba). Para
-- marcar una nueva versión como vigente, la aplicación (o un procedimiento
-- almacenado) debe hacer, en ese orden:
--   1) UPDATE alimento_version SET vigente = FALSE
--         WHERE alimento_id = :id AND vigente = TRUE;
--   2) INSERT INTO alimento_version (..., vigente) VALUES (..., TRUE);
-- ============================================================
DELIMITER $$

-- RN-15: la suma de cantidad_distribuida entre almacenes no puede exceder
-- la cantidad_solicitada de la línea de orden de compra.
CREATE TRIGGER trg_ocdistribucion_valida
BEFORE INSERT ON orden_compra_distribucion
FOR EACH ROW
BEGIN
    DECLARE v_cantidad_solicitada DECIMAL(14,4);
    DECLARE v_suma_actual DECIMAL(14,4);
    SELECT cantidad_solicitada INTO v_cantidad_solicitada
      FROM orden_compra_detalle WHERE orden_compra_detalle_id = NEW.orden_compra_detalle_id;
    SELECT COALESCE(SUM(cantidad_distribuida),0) INTO v_suma_actual
      FROM orden_compra_distribucion WHERE orden_compra_detalle_id = NEW.orden_compra_detalle_id;
    IF (v_suma_actual + NEW.cantidad_distribuida) > v_cantidad_solicitada THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'RN-15: la suma distribuida entre almacenes excede la cantidad solicitada de la OC';
    END IF;
END$$

-- RN-07: no se puede emitir una nota de salida si el stock disponible del
-- almacén es insuficiente.
CREATE TRIGGER trg_nota_salida_detalle_valida
BEFORE INSERT ON nota_salida_detalle
FOR EACH ROW
BEGIN
    DECLARE v_almacen_id INT;
    DECLARE v_producto_id INT;
    DECLARE v_disponible DECIMAL(14,4);
    SELECT ns.almacen_id, scd.producto_id
      INTO v_almacen_id, v_producto_id
      FROM nota_salida ns
      JOIN solicitud_cocina_detalle scd ON scd.solicitud_cocina_detalle_id = NEW.solicitud_cocina_detalle_id
     WHERE ns.nota_salida_id = NEW.nota_salida_id;
    SELECT stock_disponible INTO v_disponible
      FROM stock_almacen_producto
     WHERE almacen_id = v_almacen_id AND producto_id = v_producto_id;
    IF v_disponible IS NULL OR v_disponible < NEW.cantidad_despachada THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'RN-07: stock disponible insuficiente en el almacén para esta nota de salida';
    END IF;
END$$

DELIMITER ;

