-- ============================================================================
-- SIGA-UNMSM · Parche: corrige Error 1442 en alimento_version
--
-- MOVIDO desde db/init/02_patch_trigger.sql (bug real, no solo reorganización):
-- vivía dentro de db/init/, que se ejecuta automático en TODA instalación
-- nueva — pero 01_schema.sql YA incluye este fix (vigente_key + índice
-- único), así que el ALTER TABLE de abajo fallaba con "Duplicate column
-- name" en cualquier `docker compose up` desde cero. MySQL aborta el resto
-- de scripts de db/init/ apenas uno falla, así que
-- 03_carga_catalogo_nutricional.sql (el siguiente en orden alfabético)
-- NUNCA llegaba a correr — ninguna instalación fresca tenía el catálogo de
-- 1,870 alimentos, en silencio, sin ningún error visible salvo revisar
-- `docker logs <mysql>`. Encontrado al preparar datos de demo reales.
--
-- CAUSA: el trigger BEFORE INSERT ON alimento_version intentaba hacer
-- UPDATE sobre la propia tabla alimento_version. MySQL prohíbe que un
-- trigger modifique (INSERT/UPDATE/DELETE) la MISMA tabla que lo disparó
-- mientras esa tabla ya está siendo modificada por la sentencia que lo
-- invocó → "Error Code: 1442. Can't update table ... in stored function/
-- trigger because it is already used by statement which invoked this
-- stored function/trigger."
--
-- SOLUCIÓN: se elimina el trigger y se reemplaza la regla "máx. 1 versión
-- vigente por alimento" por un ÍNDICE ÚNICO sobre una columna generada
-- (patrón estándar en MySQL para "solo un TRUE por grupo", ya que MySQL no
-- soporta índices únicos parciales como PostgreSQL).
--
-- Ejecutar este parche UNA sola vez sobre la base ya creada, ANTES de
-- volver a correr 07_carga_catalogo_nutricional.sql (que ya viene
-- actualizado con INSERT IGNORE, así que es seguro re-ejecutarlo aunque
-- 'alimento' ya tenga los 1870 registros cargados).
-- ============================================================================

USE siga_unmsm;

-- 1) Elimina los triggers que causaban el error (si existen)
DROP TRIGGER IF EXISTS trg_alimento_version_vigente_ins;
DROP TRIGGER IF EXISTS trg_alimento_version_vigente_upd;

-- 2) Agrega la columna generada + índice único que reemplaza al trigger
--    (si ya la agregaste antes, MySQL avisará "Duplicate column name" y
--    puedes ignorar/comentar esta sección)
ALTER TABLE alimento_version
    ADD COLUMN vigente_key INT GENERATED ALWAYS AS (IF(vigente, alimento_id, NULL)) STORED,
    ADD UNIQUE KEY uq_alimento_version_vigente (vigente_key);

-- Verificación rápida:
-- DESCRIBE alimento_version;
-- SHOW TRIGGERS LIKE 'alimento_version';
