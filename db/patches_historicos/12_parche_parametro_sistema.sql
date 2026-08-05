-- ============================================================================
-- SIGA-UNMSM · Parche: crea la tabla parametro_sistema
--
-- Sesión 18: implementa "Parámetros del sistema" (09 Administración del
-- diseño original) — almacén clave-valor genérico, administrado solo por
-- ADMIN. Si ya creaste el esquema con una versión de 01_schema.sql
-- anterior a este parche, ejecuta esto una sola vez.
-- ============================================================================

USE siga_unmsm;

CREATE TABLE parametro_sistema (
    clave                VARCHAR(60) PRIMARY KEY,
    valor                VARCHAR(255) NOT NULL,
    descripcion          VARCHAR(255),
    actualizado_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_por_id   INT,
    CONSTRAINT fk_parametro_sistema_actualizado_por_id FOREIGN KEY (actualizado_por_id) REFERENCES usuario(usuario_id)
);
