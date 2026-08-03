# Importar todos los modelos aquí para que SQLAlchemy pueda resolver las
# relaciones entre archivos al configurar los mappers (Base.registry).
# A medida que se agreguen módulos (contratos, órdenes de compra, etc.),
# sus modelos se importan también desde este archivo.

from app.models.organizacion import (  # noqa: F401
    Almacen,
    CentroConsumo,
    Rol,
    Sede,
    UsuarioAlmacenAcceso,
)
from app.models.usuario import Usuario  # noqa: F401
from app.models.catalogos import (  # noqa: F401
    Alimento,
    AlimentoVersion,
    CategoriaAlimento,
    UnidadMedida,
)
from app.models.receta import Receta, RecetaIngrediente, RecetaValorNutricional  # noqa: F401
from app.models.planificacion import (  # noqa: F401
    MenuDia,
    MenuQuincenal,
    Plato,
    RacionAnual,
)
from app.models.dosificacion import DosificacionDetalle  # noqa: F401
