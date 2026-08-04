import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageKardexMovimientoOut } from "@/lib/api/generated/model/pageKardexMovimientoOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

const PAGE_SIZE = 20;

const TIPO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  INGRESO: "success",
  SALIDA: "warning",
  AJUSTE: "neutral",
  MERMA: "danger",
  DEVOLUCION_PROVEEDOR: "warning",
  DEVOLUCION_COCINA: "success",
  TRANSFERENCIA_SALIDA: "warning",
  TRANSFERENCIA_INGRESO: "success",
  INVENTARIO_AJUSTE: "neutral",
};

export default async function KardexPage({
  searchParams,
}: PageProps<"/almacenes/kardex">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";
  const productoId = typeof params.producto_id === "string" ? params.producto_id : "";
  const tipoMovimiento = typeof params.tipo_movimiento === "string" ? params.tipo_movimiento : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);
  if (productoId) query.set("producto_id", productoId);
  if (tipoMovimiento) query.set("tipo_movimiento", tipoMovimiento);

  const [almacenes, productos, data] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<PageKardexMovimientoOut>(`/kardex?${query.toString()}`),
  ]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <SelectFilter
          paramName="almacen_id"
          label="Almacén"
          options={[
            { value: "", label: "Todos" },
            ...almacenes.items.map((a) => ({ value: String(a.almacen_id), label: a.codigo })),
          ]}
        />
        <SelectFilter
          paramName="producto_id"
          label="Producto"
          options={[
            { value: "", label: "Todos" },
            ...productos.items.map((p) => ({ value: String(p.producto_id), label: p.codigo })),
          ]}
        />
        <SelectFilter
          paramName="tipo_movimiento"
          label="Tipo"
          options={[
            { value: "", label: "Todos" },
            { value: "INGRESO", label: "Ingreso" },
            { value: "SALIDA", label: "Salida" },
            { value: "AJUSTE", label: "Ajuste" },
            { value: "MERMA", label: "Merma" },
            { value: "DEVOLUCION_PROVEEDOR", label: "Devolución a proveedor" },
            { value: "DEVOLUCION_COCINA", label: "Devolución desde cocina" },
            { value: "TRANSFERENCIA_SALIDA", label: "Transferencia (salida)" },
            { value: "TRANSFERENCIA_INGRESO", label: "Transferencia (ingreso)" },
            { value: "INVENTARIO_AJUSTE", label: "Ajuste por inventario físico" },
          ]}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Fecha</th>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Producto</th>
              <th className="px-4 py-3 font-medium">Tipo</th>
              <th className="px-4 py-3 font-medium">Cantidad</th>
              <th className="px-4 py-3 font-medium">Saldo resultante</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  No hay movimientos de kardex para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((movimiento) => (
              <tr key={movimiento.kardex_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 text-text-secondary">{movimiento.creado_en}</td>
                <td className="px-4 py-3 text-text-secondary">{movimiento.almacen_codigo}</td>
                <td className="px-4 py-3">
                  {movimiento.producto_codigo} — {movimiento.producto_nombre}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={movimiento.tipo_movimiento}
                    variant={TIPO_VARIANT[movimiento.tipo_movimiento] ?? "neutral"}
                  />
                </td>
                <td className="px-4 py-3">{movimiento.cantidad}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {movimiento.saldo_cantidad_resultante}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4">
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} />
        </div>
      </div>
    </div>
  );
}
