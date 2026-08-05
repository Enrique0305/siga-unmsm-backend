-- ============================================================================
-- SIGA-UNMSM · Parche: agrega proveedor_id a usuario
--
-- Sesión 12: cierra el hueco de alcance del rol PROVEEDOR — sin esta
-- columna, un usuario con rol PROVEEDOR ve/toca los contratos, órdenes de
-- compra y guías de remisión de TODOS los proveedores, no solo los
-- propios. Si ya creaste la tabla `usuario` con una versión de
-- 01_schema.sql anterior a este parche, ejecuta esto una sola vez.
-- ============================================================================

USE siga_unmsm;

ALTER TABLE usuario
    ADD COLUMN proveedor_id INT NULL AFTER sede_id,
    ADD CONSTRAINT fk_usuario_proveedor_id FOREIGN KEY (proveedor_id) REFERENCES proveedor(proveedor_id);
