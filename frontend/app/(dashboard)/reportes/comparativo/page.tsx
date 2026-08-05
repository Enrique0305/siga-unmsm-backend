import { ComparativoConsumoForm } from "@/components/reportes/ComparativoConsumoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { ComparativoConsumoOut } from "@/lib/api/generated/model/comparativoConsumoOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";
import type { PageProveedorOut } from "@/lib/api/generated/model/pageProveedorOut";

export default async function ComparativoConsumoPage({
  searchParams,
}: PageProps<"/reportes/comparativo">) {
  const params = await searchParams;
  const productoId = typeof params.producto_id === "string" ? params.producto_id : "";
  const fechaInicio = typeof params.fecha_inicio === "string" ? params.fecha_inicio : "";
  const fechaFin = typeof params.fecha_fin === "string" ? params.fecha_fin : "";
  const proveedorId = typeof params.proveedor_id === "string" ? params.proveedor_id : "";

  const query = new URLSearchParams();
  query.set("producto_id", productoId);
  query.set("fecha_inicio", fechaInicio);
  query.set("fecha_fin", fechaFin);
  if (proveedorId) query.set("proveedor_id", proveedorId);

  const [productos, proveedores, comparativo] = await Promise.all([
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<PageProveedorOut>("/proveedores?page_size=100"),
    productoId && fechaInicio && fechaFin
      ? serverFetch<ComparativoConsumoOut>(`/reportes/comparativo-consumo?${query.toString()}`)
      : Promise.resolve(null),
  ]);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border/20 bg-white p-4">
        <ComparativoConsumoForm productos={productos.items} proveedores={proveedores.items} />
      </div>

      {comparativo && (
        <div className="rounded-lg border border-border/20 bg-white p-6">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            {comparativo.producto_codigo} — {comparativo.producto_nombre} ({comparativo.fecha_inicio} a{" "}
            {comparativo.fecha_fin})
          </h3>
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-text-secondary">Teórico (BOM)</dt>
              <dd className="text-lg font-semibold">{comparativo.cantidad_teorica}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Comprado</dt>
              <dd className="text-lg font-semibold">{comparativo.cantidad_comprada}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Recibido</dt>
              <dd className="text-lg font-semibold">{comparativo.cantidad_recibida}</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Despachado</dt>
              <dd className="text-lg font-semibold">{comparativo.cantidad_despachada}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}
