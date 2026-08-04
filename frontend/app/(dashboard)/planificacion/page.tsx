import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { PageRacionAnualOut } from "@/lib/api/generated/model/pageRacionAnualOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];
const PAGE_SIZE = 20;

export default async function RacionesAnualesPage({
  searchParams,
}: PageProps<"/planificacion">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  const [session, data, sedes, centros] = await Promise.all([
    getSession(),
    serverFetch<PageRacionAnualOut>(`/planificacion/raciones-anuales?page=${page}&page_size=${PAGE_SIZE}`),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const sedeNombre = new Map(sedes.map((s) => [s.sede_id, s.nombre]));
  const centroNombre = new Map(centros.map((c) => [c.centro_consumo_id, c.nombre]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-end gap-3">
        {puedeEditar && (
          <Link
            href="/planificacion/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva ración anual
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Año</th>
              <th className="px-4 py-3 font-medium">Sede</th>
              <th className="px-4 py-3 font-medium">Centro de consumo</th>
              <th className="px-4 py-3 font-medium">Población</th>
              <th className="px-4 py-3 font-medium">Raciones/día</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  No hay raciones anuales para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((racion) => (
              <tr key={racion.racion_anual_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/planificacion/${racion.racion_anual_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {racion.anio}
                  </Link>
                </td>
                <td className="px-4 py-3">{sedeNombre.get(racion.sede_id) ?? `#${racion.sede_id}`}</td>
                <td className="px-4 py-3">{centroNombre.get(racion.centro_consumo_id) ?? `#${racion.centro_consumo_id}`}</td>
                <td className="px-4 py-3 text-text-secondary">{racion.poblacion_atendida}</td>
                <td className="px-4 py-3 text-text-secondary">{racion.raciones_dia}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={racion.estado}
                    variant={racion.estado === "APROBADO" ? "success" : "neutral"}
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
