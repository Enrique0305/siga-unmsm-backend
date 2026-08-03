from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base declarativa para todos los modelos ORM. Las tablas físicas ya
    existen en MySQL (creadas por db/init/01_schema.sql); estos modelos
    solo las MAPEAN — no se usa Base.metadata.create_all() en ningún lado.
    Alembic se usa únicamente para futuros cambios incrementales al esquema.
    """
    pass
