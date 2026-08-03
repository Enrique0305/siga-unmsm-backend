-- ============================================================================
-- SIGA-UNMSM · Parche: agrega password_hash a usuario
--
-- Necesario para el backend de autenticación (FastAPI + JWT). Si ya creaste
-- la tabla `usuario` con el script 02_modelo_base_datos_v4_mysql.sql (versión
-- anterior a este parche), ejecuta esto una sola vez.
-- ============================================================================

USE siga_unmsm;

ALTER TABLE usuario
    ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT '' AFTER correo;

-- Quita el DEFAULT '' después de fijar contraseñas reales a tus usuarios
-- existentes (el default vacío es solo para que el ALTER no falle si ya
-- hay filas). Ejemplo para crear el primer usuario administrador:
--
-- Genera el hash bcrypt desde Python:
--   from passlib.context import CryptContext
--   pwd = CryptContext(schemes=["bcrypt"]).hash("TU_PASSWORD_SEGURO")
--
-- INSERT INTO usuario (nombres, apellidos, correo, password_hash, rol_id, estado)
-- VALUES ('Admin', 'SIGA', 'admin@unmsm.edu.pe', '<hash_generado>', 1, 'ACTIVO');

ALTER TABLE usuario ALTER COLUMN password_hash DROP DEFAULT;
