import Link from "next/link";

import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageGuiaRemisionListOut } from "@/lib/api/generated/model/pageGuiaRemisionListOut";
import type { PageIngresoAlmacenOut } from "@/lib/api/generated/model/pageIngresoAlmacenOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];
const PAGE_SIZE = 20;

export default async function IngresosAlmacenPage({
  searchParams,
}: PageProps<"/almacenes/ingresos">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);

  const [session, almacenes, guias, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageGuiaRemisionListOut>("/guias-remision?page_size=100"),
    serverFetch<PageIngresoAlmacenOut>(`/ingresos-almacen?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, `${a.codigo} — ${a.nombre}`]));
  const numeroGuia = new Map(guias.items.map((g) => [g.guia_remision_id, g.numero_guia]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SelectFilter
          paramName="almacen_id"
          label="Almacén"
          options={[
            { value: "", label: "Todos" },
            ...almacenes.items.map((a) => ({ value: String(a.almacen_id), label: a.codigo })),
          ]}
        />
        {puedeEditar && (
          <Link
            href="/almacenes/ingresos/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo ingreso
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° ingreso</th>
              <th className="px-4 py-3 font-medium">Guía</th>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay ingresos para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((ingreso) => (
              <tr key={ingreso.ingreso_almacen_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/almacenes/ingresos/${ingreso.ingreso_almacen_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {ingreso.numero_ingreso}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {numeroGuia.get(ingreso.guia_remision_id) ?? `#${ingreso.guia_remision_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(ingreso.almacen_id) ?? `#${ingreso.almacen_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">{ingreso.fecha_ingreso}</td>
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
