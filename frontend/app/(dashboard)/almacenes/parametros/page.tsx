import { EliminarParametroButton } from "@/components/almacenes/EliminarParametroButton";
import { ParametroStockForm } from "@/components/almacenes/ParametroStockForm";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageAlmacenProductoParametroOut } from "@/lib/api/generated/model/pageAlmacenProductoParametroOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

export default async function ParametrosStockPage({
  searchParams,
}: PageProps<"/almacenes/parametros">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);

  const [session, almacenes, productos, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<PageAlmacenProductoParametroOut>(`/parametros-stock?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      {puedeEditar && <ParametroStockForm almacenes={almacenes.items} productos={productos.items} />}

      <SelectFilter
        paramName="almacen_id"
        label="Almacén"
        options={[
          { value: "", label: "Todos" },
          ...almacenes.items.map((a) => ({ value: String(a.almacen_id), label: a.codigo })),
        ]}
      />

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Producto</th>
              <th className="px-4 py-3 font-medium">Stock mínimo</th>
              {puedeEditar && <th className="px-4 py-3 font-medium">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={puedeEditar ? 4 : 3} className="px-4 py-8 text-center text-text-secondary">
                  No hay parámetros de stock configurados — se usa el mínimo referencial global de
                  cada producto.
                </td>
              </tr>
            )}
            {data.items.map((parametro) => (
              <tr key={`${parametro.almacen_id}-${parametro.producto_id}`} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 text-text-secondary">{parametro.almacen_codigo}</td>
                <td className="px-4 py-3">
                  {parametro.producto_codigo} — {parametro.producto_nombre}
                </td>
                <td className="px-4 py-3">{parametro.stock_minimo}</td>
                {puedeEditar && (
                  <td className="px-4 py-3">
                    <EliminarParametroButton
                      almacenId={parametro.almacen_id}
                      productoId={parametro.producto_id}
                    />
                  </td>
                )}
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
