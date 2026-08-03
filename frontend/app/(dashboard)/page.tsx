import { StatCard } from "@/components/ui/StatCard";
import { serverFetch } from "@/lib/api/server-fetch";
import type { AlertasAlmacenOut } from "@/lib/api/generated/model/alertasAlmacenOut";
import type { PageInformeConformidadPagoOut } from "@/lib/api/generated/model/pageInformeConformidadPagoOut";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";
import type { ValorizacionAlmacenOut } from "@/lib/api/generated/model/valorizacionAlmacenOut";

const currencyFormatter = new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
});

async function fetchSafely<T>(path: string): Promise<T | null> {
  try {
    return await serverFetch<T>(path);
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const [valorizacion, alertas, ordenesCompra, informesPago] =
    await Promise.all([
      fetchSafely<ValorizacionAlmacenOut[]>(
        "/reportes/valorizacion-inventario",
      ),
      fetchSafely<AlertasAlmacenOut>("/reportes/alertas?dias_vencimiento=30"),
      fetchSafely<PageOrdenCompraOut>(
        "/ordenes-compra?estado=EMITIDA&page_size=1",
      ),
      fetchSafely<PageInformeConformidadPagoOut>(
        "/informes-conformidad-pago?estado=ENVIADO&page_size=1",
      ),
    ]);

  const valorTotal = valorizacion?.reduce(
    (sum, fila) => sum + fila.valor_valorizado_total,
    0,
  );

  const totalAlertas = alertas
    ? alertas.stock_bajo.length +
      alertas.proximos_vencer.length +
      alertas.observaciones_sin_resolver.length
    : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Dashboard ejecutivo
        </h1>
        <p className="text-sm text-text-secondary">
          Resumen consolidado de todos los almacenes.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Valorización de inventario"
          value={
            valorTotal !== undefined
              ? currencyFormatter.format(valorTotal)
              : "No disponible"
          }
          variant="primary"
          hint="Suma de todos los almacenes"
        />
        <StatCard
          label="Alertas activas"
          value={totalAlertas !== null ? String(totalAlertas) : "No disponible"}
          variant={
            totalAlertas !== null && totalAlertas > 0 ? "warning" : "success"
          }
          hint="Stock bajo, próximos a vencer y observaciones sin resolver"
        />
        <StatCard
          label="Órdenes de compra emitidas"
          value={
            ordenesCompra !== null ? String(ordenesCompra.total) : "No disponible"
          }
          variant="primary"
          hint="Pendientes de guía de remisión"
        />
        <StatCard
          label="Informes de pago enviados"
          value={
            informesPago !== null ? String(informesPago.total) : "No disponible"
          }
          variant="warning"
          hint="Pendientes de estado de pago"
        />
      </div>

      {alertas && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <AlertaLista
            titulo="Stock bajo"
            cantidad={alertas.stock_bajo.length}
            variant="danger"
          />
          <AlertaLista
            titulo="Próximos a vencer"
            cantidad={alertas.proximos_vencer.length}
            variant="warning"
          />
          <AlertaLista
            titulo="Observaciones sin resolver"
            cantidad={alertas.observaciones_sin_resolver.length}
            variant="danger"
          />
        </div>
      )}
    </div>
  );
}

function AlertaLista({
  titulo,
  cantidad,
  variant,
}: {
  titulo: string;
  cantidad: number;
  variant: "danger" | "warning";
}) {
  return (
    <div className="rounded-lg border border-border/20 bg-white p-5">
      <p className="text-sm font-medium text-text-secondary">{titulo}</p>
      <p
        className={`mt-2 text-2xl font-semibold ${
          cantidad > 0
            ? variant === "danger"
              ? "text-danger"
              : "text-warning"
            : "text-success"
        }`}
      >
        {cantidad}
      </p>
    </div>
  );
}
