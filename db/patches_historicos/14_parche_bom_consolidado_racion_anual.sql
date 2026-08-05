-- ============================================================================
-- SIGA-UNMSM · Parche: agrega racion_anual_id a bom_consolidado
--
-- Deuda técnica (tras Sesión 21): bom_consolidado nunca tuvo una columna
-- que la ligue a la RacionAnual que la generó — crud/bom_consolidado.py
-- scopeaba el reemplazo idempotente y la lectura por año calendario
-- (tipo_periodo="ANIO" + periodo_inicio/fin), así que dos RacionAnual del
-- mismo año que consolidan el mismo almacén+producto hacían que la
-- segunda reemplazara silenciosamente la foto de la primera. Nullable
-- porque no hay forma de backfillear correctamente las filas ya
-- existentes (la relación real nunca se guardó) — si ya creaste el
-- esquema con una versión de 01_schema.sql anterior a este parche,
-- ejecuta esto una sola vez.
-- ============================================================================

USE siga_unmsm;

ALTER TABLE bom_consolidado
    ADD COLUMN racion_anual_id INT NULL AFTER bom_consolidado_id,
    ADD CONSTRAINT fk_bom_consolidado_racion_anual_id FOREIGN KEY (racion_anual_id) REFERENCES racion_anual(racion_anual_id);
