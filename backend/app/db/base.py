from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base declarativa para todos los modelos ORM. Las tablas físicas ya
    existen en MySQL (creadas por db/init/01_schema.sql); estos modelos
    solo las MAPEAN — no se usa Base.metadata.create_all() en ningún lado.
    Alembic se usa únicamente para futuros cambios incrementales al esquema.
    """
    pass


# PK BIGINT AUTO_INCREMENT (kardex_movimiento, bin_card_movimiento,
# auditoria_log, ...): SQLite solo alía el rowid (autoincrement real) en
# columnas declaradas exactamente INTEGER, no BIGINT. Como los tests corren
# Base.metadata.create_all() contra SQLite (nunca contra MySQL), hay que
# mapear estas PK con este tipo — en MySQL sigue siendo BIGINT, en SQLite se
# crea como INTEGER y autoincrementa. Ver CLAUDE.md sección 7.4.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")
