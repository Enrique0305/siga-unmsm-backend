import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

export default async function AlmacenesPage({
  searchParams,
}: PageProps<"/almacenes">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>(`/almacenes?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SelectFilter
          paramName="estado"
          label="Estado"
          options={[
            { value: "", label: "Todos" },
            { value: "ACTIVO", label: "Activo" },
            { value: "INACTIVO", label: "Inactivo" },
          ]}
        />
        {puedeEditar && (
          <Link
            href="/almacenes/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo almacén
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Código</th>
              <th className="px-4 py-3 font-medium">Nombre</th>
              <th className="px-4 py-3 font-medium">Tipo comedor</th>
              <th className="px-4 py-3 font-medium">Estado</th>
              {puedeEditar && <th className="px-4 py-3 font-medium" />}
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td
                  colSpan={puedeEditar ? 5 : 4}
                  className="px-4 py-8 text-center text-text-secondary"
                >
                  No hay almacenes para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((almacen) => (
              <tr key={almacen.almacen_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 font-mono text-xs">{almacen.codigo}</td>
                <td className="px-4 py-3">{almacen.nombre}</td>
                <td className="px-4 py-3 text-text-secondary">{almacen.tipo_comedor}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={almacen.estado}
                    variant={almacen.estado === "ACTIVO" ? "success" : "neutral"}
                  />
                </td>
                {puedeEditar && (
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/almacenes/${almacen.almacen_id}/editar`}
                      className="text-primary hover:underline"
                    >
                      Editar
                    </Link>
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
