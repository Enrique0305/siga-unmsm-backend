-- ============================================================================
-- SIGA-UNMSM · Parche: crea la tabla notificacion
--
-- Sesión 20: implementa los jobs automáticos de RN-11 (plazo vencido de
-- subsanación) y RN-12 (alertas de contrato) — esta tabla guarda las
-- notificaciones que genera el job diario de RN-12 ("Notificación a
-- Logística"), consultables vía GET /notificaciones (sin infraestructura
-- de email en el proyecto). Si ya creaste el esquema con una versión de
-- 01_schema.sql anterior a este parche, ejecuta esto una sola vez.
-- ============================================================================

USE siga_unmsm;

CREATE TABLE notificacion (
    notificacion_id      INT AUTO_INCREMENT PRIMARY KEY,
    tipo                 VARCHAR(40) NOT NULL,
    referencia_id        INT NOT NULL,
    mensaje              VARCHAR(255) NOT NULL,
    leida                BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
