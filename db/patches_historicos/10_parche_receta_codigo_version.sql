-- ============================================================================
-- SIGA-UNMSM · Parche: corrige unicidad de receta.codigo
--
-- BUG: la tabla `receta` se creó con `codigo VARCHAR(30) UNIQUE NOT NULL`.
-- Eso choca directamente con RN-25 (versionamiento): al crear una nueva
-- versión de una receta aprobada/vigente, se inserta una FILA NUEVA con el
-- MISMO codigo y version+1 — y el UNIQUE(codigo) la rechaza.
--
-- FIX: la unicidad debe ser sobre (codigo, version), no sobre codigo solo.
-- Ejecutar este parche una sola vez si ya creaste la tabla `receta` con el
-- esquema anterior.
-- ============================================================================

USE siga_unmsm;

-- El nombre del índice implícito de una columna UNIQUE en MySQL es, por
-- defecto, el propio nombre de la columna. Si tu instalación le puso otro
-- nombre, revísalo antes con:
--   SHOW INDEX FROM receta WHERE Key_name != 'PRIMARY';
ALTER TABLE receta DROP INDEX codigo;

ALTER TABLE receta ADD UNIQUE KEY uq_receta_codigo_version (codigo, version);
