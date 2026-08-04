import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

const PAGE_SIZE = 20;

export default async function AdministracionProductosPage({
  searchParams,
}: PageProps<"/administracion/productos">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "ACTIVO";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const query = new URLSearchParams();
  query.set("page", String(page));
  query.set("page_size", String(PAGE_SIZE));
  if (estado) query.set("estado", estado);
  if (buscar) query.set("buscar", buscar);

  const data = await serverFetch<PageProductoOut>(`/productos?${query.toString()}`);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por código o nombre..." />
          <SelectFilter
            paramName="estado"
            label="Estado"
            options={[
              { value: "ACTIVO", label: "Activos" },
              { value: "INACTIVO", label: "Inactivos" },
              { value: "", label: "Todos" },
            ]}
          />
        </div>
        <Link
          href="/administracion/productos/nuevo"
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Nuevo producto
        </Link>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Código</th>
              <th className="px-4 py-3 font-medium">Nombre</th>
              <th className="px-4 py-3 font-medium">Categoría</th>
              <th className="px-4 py-3 font-medium">Unidad</th>
              <th className="px-4 py-3 font-medium">Estado</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  No hay productos para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((producto) => (
              <tr key={producto.producto_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 font-mono text-xs">{producto.codigo}</td>
                <td className="px-4 py-3">{producto.nombre}</td>
                <td className="px-4 py-3 text-text-secondary">{producto.categoria ?? "—"}</td>
                <td className="px-4 py-3 text-text-secondary">{producto.unidad.codigo}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={producto.estado}
                    variant={producto.estado === "ACTIVO" ? "success" : "neutral"}
                  />
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/administracion/productos/${producto.producto_id}/editar`}
                    className="text-primary hover:underline"
                  >
                    Editar
                  </Link>
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
