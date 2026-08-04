import Link from "next/link";

import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageGuiaRemisionListOut } from "@/lib/api/generated/model/pageGuiaRemisionListOut";
import type { PageInspeccionOut } from "@/lib/api/generated/model/pageInspeccionOut";

const ROLES_EDICION = ["ADMIN", "INSPECTOR"];
const PAGE_SIZE = 20;

export default async function InspeccionesPage({
  searchParams,
}: PageProps<"/recepcion">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });

  const [session, data, guias] = await Promise.all([
    getSession(),
    serverFetch<PageInspeccionOut>(`/inspecciones?${query.toString()}`),
    serverFetch<PageGuiaRemisionListOut>("/guias-remision?page_size=100"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const numeroGuia = new Map(guias.items.map((g) => [g.guia_remision_id, g.numero_guia]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-text-secondary">
          Registro de inspecciones sobre guías de remisión recibidas.
        </p>
        {puedeEditar && (
          <Link
            href="/recepcion/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva inspección
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Inspección</th>
              <th className="px-4 py-3 font-medium">Guía</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-text-secondary">
                  No hay inspecciones para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((inspeccion) => (
              <tr key={inspeccion.inspeccion_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/recepcion/${inspeccion.inspeccion_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    #{inspeccion.inspeccion_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {numeroGuia.get(inspeccion.guia_remision_id) ?? `#${inspeccion.guia_remision_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">{inspeccion.fecha_inspeccion}</td>
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
