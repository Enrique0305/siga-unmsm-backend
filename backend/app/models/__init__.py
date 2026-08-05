# Importar todos los modelos aquí para que SQLAlchemy pueda resolver las
# relaciones entre archivos al configurar los mappers (Base.registry).
# A medida que se agreguen módulos (contratos, órdenes de compra, etc.),
# sus modelos se importan también desde este archivo.

from app.models.organizacion import (  # noqa: F401
    Almacen,
    CentroConsumo,
    Rol,
    Sede,
    UbicacionInterna,
    UsuarioAlmacenAcceso,
)
from app.models.usuario import Usuario  # noqa: F401
from app.models.catalogos import (  # noqa: F401
    Alimento,
    AlimentoVersion,
    CategoriaAlimento,
    Producto,
    UnidadMedida,
)
from app.models.receta import Receta, RecetaIngrediente, RecetaValorNutricional  # noqa: F401
from app.models.planificacion import (  # noqa: F401
    MenuDia,
    MenuQuincenal,
    Plato,
    RacionAnual,
    RequerimientoAnual,
    RequerimientoAnualDetalle,
)
from app.models.dosificacion import BomConsolidado, DosificacionDetalle  # noqa: F401
from app.models.contratos import (  # noqa: F401
    Contrato,
    CronogramaEntrega,
    ProductoContratado,
    Proveedor,
)
from app.models.compras import (  # noqa: F401
    AutorizacionExcedente,
    GuiaRemision,
    GuiaRemisionDetalle,
    OrdenCompra,
    OrdenCompraDetalle,
    OrdenCompraDistribucion,
    PedidoSemanal,
)
from app.models.inspeccion import (  # noqa: F401
    ActaObservacion,
    Inspeccion,
    InspeccionDetalle,
    Subsanacion,
)
from app.models.inventario import (  # noqa: F401
    AjusteInventario,
    AlmacenProductoParametro,
    BinCardMovimiento,
    Devolucion,
    IngresoAlmacen,
    IngresoAlmacenDetalle,
    InventarioFisico,
    InventarioFisicoDetalle,
    KardexMovimiento,
    Merma,
    StockAlmacenProducto,
    TransferenciaAlmacen,
    TransferenciaAlmacenDetalle,
)
from app.models.cocina import (  # noqa: F401
    NotaSalida,
    NotaSalidaDetalle,
    SolicitudCocina,
    SolicitudCocinaDetalle,
)
from app.models.pagos import (  # noqa: F401
    InformeConformidadDetalle,
    InformeConformidadPago,
    Penalidad,
)
from app.models.auditoria import AuditoriaLog  # noqa: F401
from app.models.sistema import ParametroSistema  # noqa: F401
