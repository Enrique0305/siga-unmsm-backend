import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";
import type { PageStockAlmacenProductoOut } from "@/lib/api/generated/model/pageStockAlmacenProductoOut";

const PAGE_SIZE = 20;

export default async function StockAlmacenPage({
  searchParams,
}: PageProps<"/almacenes/stock">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";
  const productoId = typeof params.producto_id === "string" ? params.producto_id : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);
  if (productoId) query.set("producto_id", productoId);

  const [almacenes, productos, data] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<PageStockAlmacenProductoOut>(`/stock-almacen?${query.toString()}`),
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
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Producto</th>
              <th className="px-4 py-3 font-medium">Físico</th>
              <th className="px-4 py-3 font-medium">Comprometido</th>
              <th className="px-4 py-3 font-medium">Disponible</th>
              <th className="px-4 py-3 font-medium">Costo promedio</th>
              <th className="px-4 py-3 font-medium">Valorizado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-text-secondary">
                  No hay stock para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((stock) => (
              <tr
                key={`${stock.almacen_id}-${stock.producto_id}`}
                className="border-b border-border/10 last:border-0"
              >
                <td className="px-4 py-3 text-text-secondary">
                  {stock.almacen_codigo} — {stock.almacen_nombre}
                </td>
                <td className="px-4 py-3">
                  {stock.producto_codigo} — {stock.producto_nombre}
                </td>
                <td className="px-4 py-3">{stock.stock_fisico}</td>
                <td className="px-4 py-3 text-text-secondary">{stock.stock_comprometido}</td>
                <td className="px-4 py-3">{stock.stock_disponible}</td>
                <td className="px-4 py-3 text-text-secondary">
                  S/ {stock.valor_promedio_unitario.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  S/ {stock.valor_valorizado.toFixed(2)}
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
