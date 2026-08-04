import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageInventarioFisicoOut } from "@/lib/api/generated/model/pageInventarioFisicoOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "warning" | "success"> = {
  EN_PROCESO: "warning",
  CERRADO: "success",
};

export default async function InventariosFisicosPage({
  searchParams,
}: PageProps<"/almacenes/inventarios">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);
  if (estado) query.set("estado", estado);

  const [session, almacenes, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageInventarioFisicoOut>(`/inventarios-fisicos?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, `${a.codigo} — ${a.nombre}`]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
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
            paramName="estado"
            label="Estado"
            options={[
              { value: "", label: "Todos" },
              { value: "EN_PROCESO", label: "En proceso" },
              { value: "CERRADO", label: "Cerrado" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/almacenes/inventarios/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo inventario físico
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Fecha de conteo</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-text-secondary">
                  No hay inventarios físicos para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((inventario) => (
              <tr key={inventario.inventario_fisico_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/almacenes/inventarios/${inventario.inventario_fisico_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {nombreAlmacen.get(inventario.almacen_id) ?? `#${inventario.almacen_id}`}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">{inventario.fecha_conteo}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={inventario.estado}
                    variant={ESTADO_VARIANT[inventario.estado] ?? "warning"}
                  />
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
