"""baseline: esquema ya creado por db/init/01_schema.sql (fuera de Alembic)

Esta migración es intencionalmente un no-op. El esquema completo (60
tablas) se creó manualmente con los scripts SQL versionados del proyecto
(02_modelo_base_datos_v4_mysql.sql y sus parches), no con Alembic.

Al levantar un entorno NUEVO con `docker compose up`, MySQL ejecuta esos
scripts automáticamente vía /docker-entrypoint-initdb.d. Después de eso,
hay que "sellar" Alembic en este punto de partida sin volver a crear nada:

    docker compose exec api alembic stamp head

A partir de ahí, cualquier cambio de esquema se hace con:

    docker compose exec api alembic revision --autogenerate -m "descripcion"
    docker compose exec api alembic upgrade head

Revision ID: 0001
Revises:
Create Date: 2026-07-25

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass  # el esquema ya existe, ver docstring arriba


def downgrade() -> None:
    pass
