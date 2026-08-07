"""
Siembra de datos iniciales: roles, sedes, los 4 almacenes de la
especificación funcional, un centro de consumo por almacén, unidades de
medida base, y el primer usuario administrador.

Uso (con los contenedores levantados):
    docker compose exec api python -m app.seed

Es idempotente: si ya existen los registros (por código/nombre/correo),
los salta en vez de duplicarlos.

Nota: centro_consumo y unidad_medida no tienen ningún endpoint de
creación en la API (catalogos.py es de solo lectura, ver CLAUDE.md sección
9) — sin este seed, una instalación nueva queda sin forma de crear una
Ración Anual (exige sede+centro de consumo) ni un Producto (exige unidad
de medida) desde la propia aplicación.
"""
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.catalogos import UnidadMedida
from app.models.organizacion import Almacen, CentroConsumo, Rol, Sede
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

# Un centro de consumo por almacén — mismo código base, nombre "Comedor <sede>".
# (codigo_almacen, nombre_centro)
CENTROS_CONSUMO = [
    ("ALM-CU", "Comedor Ciudad Universitaria"),
    ("ALM-CAN", "Comedor Cangallo"),
    ("ALM-VET", "Comedor Veterinaria"),
    ("ALM-ADM", "Comedor Administrativos y Docentes"),
]

# (codigo, nombre) — unidades base para el catálogo logístico (Producto).
UNIDADES_MEDIDA = [
    ("KG", "Kilogramo"),
    ("G", "Gramo"),
    ("L", "Litro"),
    ("UND", "Unidad"),
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
        almacenes_by_codigo: dict[str, Almacen] = {}
        for codigo, nombre, sede_nombre, tipo_comedor in ALMACENES:
            existente = (await db.execute(select(Almacen).where(Almacen.codigo == codigo))).scalar_one_or_none()
            if existente is None:
                existente = Almacen(
                    codigo=codigo,
                    nombre=nombre,
                    sede_id=sedes_by_nombre[sede_nombre].sede_id,
                    tipo_comedor=tipo_comedor,
                    responsable_id=admin.usuario_id,
                    estado="ACTIVO",
                )
                db.add(existente)
                await db.flush()
                print(f"  + almacén {codigo}")
            almacenes_by_codigo[codigo] = existente

        # ---- centros de consumo (uno por almacén) ----
        # Sin esto, RacionAnual no se puede crear (exige sede+centro de
        # consumo) — catalogos.py es de solo lectura, no hay otra forma de
        # sembrarlos desde la aplicación.
        for codigo_almacen, nombre_centro in CENTROS_CONSUMO:
            existente = (
                await db.execute(select(CentroConsumo).where(CentroConsumo.nombre == nombre_centro))
            ).scalar_one_or_none()
            if existente is None:
                almacen = almacenes_by_codigo[codigo_almacen]
                db.add(
                    CentroConsumo(
                        sede_id=almacen.sede_id,
                        almacen_id=almacen.almacen_id,
                        nombre=nombre_centro,
                    )
                )
                print(f"  + centro de consumo {nombre_centro}")

        # ---- unidades de medida ----
        # Sin esto, Producto no se puede crear (exige unidad_id) — mismo
        # motivo que arriba, catalogos.py no tiene forma de crearlas.
        for codigo, nombre in UNIDADES_MEDIDA:
            existente = (
                await db.execute(select(UnidadMedida).where(UnidadMedida.codigo == codigo))
            ).scalar_one_or_none()
            if existente is None:
                db.add(UnidadMedida(codigo=codigo, nombre=nombre))
                print(f"  + unidad de medida {codigo}")

        await db.commit()
        print("\nSiembra completa.")
        print(f"Inicia sesión con: {ADMIN_CORREO} / {ADMIN_PASSWORD}  (cámbiala de inmediato)")


if __name__ == "__main__":
    asyncio.run(seed())
