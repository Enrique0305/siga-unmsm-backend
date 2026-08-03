"""
Siembra de datos iniciales: roles, sedes, los 4 almacenes de la
especificación funcional, y el primer usuario administrador.

Uso (con los contenedores levantados):
    docker compose exec api python -m app.seed

Es idempotente: si ya existen los registros (por código/nombre/correo),
los salta en vez de duplicarlos.
"""
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.organizacion import Almacen, Rol, Sede
from app.models.usuario import Usuario

ROLES = [
    # (nombre, acceso_todos_almacenes, descripcion)
    ("ADMIN", True, "Administrador del sistema"),
    ("NUTRICION", False, "Planificación / Nutrición (incluye Nutricionista autorizado)"),
    ("LOGISTICA_CENTRAL", True, "Logística / Abastecimiento central"),
    ("ALMACENERO", False, "Almacenero — alcance limitado a sus almacenes"),
    ("INSPECTOR", False, "Inspector de calidad y cantidad"),
    ("COCINA", False, "Personal de cocina — alcance limitado a su almacén/comedor"),
    ("PAGOS", True, "Oficina de Abastecimiento / Pagos"),
    ("PROVEEDOR", False, "Portal de proveedor (solo lectura + carga de guías)"),
]

SEDES = [
    "Ciudad Universitaria",
    "Cangallo",
    "Veterinaria",
]

# (codigo, nombre, sede, tipo_comedor)
ALMACENES = [
    ("ALM-CU", "Almacén Comedor de Alumnos – Ciudad Universitaria", "Ciudad Universitaria", "ESTUDIANTES"),
    ("ALM-CAN", "Almacén Comedor de Alumnos – Cangallo", "Cangallo", "ESTUDIANTES"),
    ("ALM-VET", "Almacén Comedor de Alumnos – Veterinaria", "Veterinaria", "ESTUDIANTES"),
    ("ALM-ADM", "Almacén Comedor de Administrativos y Docentes", "Ciudad Universitaria", "ADMINISTRATIVOS_DOCENTES"),
]

ADMIN_CORREO = "admin@unmsm.edu.pe"
ADMIN_PASSWORD = "CambiarEnProduccion123!"  # cambiar inmediatamente después del primer login


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ---- roles ----
        roles_by_nombre: dict[str, Rol] = {}
        for nombre, acceso_todos, descripcion in ROLES:
            existente = (await db.execute(select(Rol).where(Rol.nombre == nombre))).scalar_one_or_none()
            if existente is None:
                existente = Rol(nombre=nombre, acceso_todos_almacenes=acceso_todos, descripcion=descripcion)
                db.add(existente)
                await db.flush()
                print(f"  + rol {nombre}")
            roles_by_nombre[nombre] = existente

        # ---- sedes ----
        sedes_by_nombre: dict[str, Sede] = {}
        for nombre in SEDES:
            existente = (await db.execute(select(Sede).where(Sede.nombre == nombre))).scalar_one_or_none()
            if existente is None:
                existente = Sede(nombre=nombre)
                db.add(existente)
                await db.flush()
                print(f"  + sede {nombre}")
            sedes_by_nombre[nombre] = existente

        await db.flush()

        # ---- admin (se necesita ANTES de crear almacenes, que exigen responsable_id) ----
        admin = (await db.execute(select(Usuario).where(Usuario.correo == ADMIN_CORREO))).scalar_one_or_none()
        if admin is None:
            admin = Usuario(
                nombres="Administrador",
                apellidos="SIGA-UNMSM",
                correo=ADMIN_CORREO,
                password_hash=hash_password(ADMIN_PASSWORD),
                rol_id=roles_by_nombre["ADMIN"].rol_id,
                estado="ACTIVO",
            )
            db.add(admin)
            await db.flush()
            print(f"  + usuario admin ({ADMIN_CORREO} / contraseña temporal: {ADMIN_PASSWORD})")

        # ---- almacenes ----
        for codigo, nombre, sede_nombre, tipo_comedor in ALMACENES:
            existente = (await db.execute(select(Almacen).where(Almacen.codigo == codigo))).scalar_one_or_none()
            if existente is None:
                db.add(
                    Almacen(
                        codigo=codigo,
                        nombre=nombre,
                        sede_id=sedes_by_nombre[sede_nombre].sede_id,
                        tipo_comedor=tipo_comedor,
                        responsable_id=admin.usuario_id,
                        estado="ACTIVO",
                    )
                )
                print(f"  + almacén {codigo}")

        await db.commit()
        print("\nSiembra completa.")
        print(f"Inicia sesión con: {ADMIN_CORREO} / {ADMIN_PASSWORD}  (cámbiala de inmediato)")


if __name__ == "__main__":
    asyncio.run(seed())
