import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageSolicitudCocinaOut } from "@/lib/api/generated/model/pageSolicitudCocinaOut";

const ROLES_EDICION = ["ADMIN", "COCINA"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "warning" | "success" | "neutral"> = {
  PENDIENTE: "warning",
  DESPACHADA: "success",
  ANULADA: "neutral",
};

export default async function SolicitudesCocinaPage({
  searchParams,
}: PageProps<"/cocina">) {
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
    serverFetch<PageSolicitudCocinaOut>(`/solicitudes-cocina?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, a.codigo]));

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
              { value: "PENDIENTE", label: "Pendiente" },
              { value: "DESPACHADA", label: "Despachada" },
              { value: "ANULADA", label: "Anulada" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/cocina/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva solicitud
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° solicitud</th>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay solicitudes de cocina para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((solicitud) => (
              <tr key={solicitud.solicitud_cocina_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/cocina/${solicitud.solicitud_cocina_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {solicitud.numero_solicitud}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(solicitud.almacen_id) ?? `#${solicitud.almacen_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">{solicitud.creado_en}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={solicitud.estado}
                    variant={ESTADO_VARIANT[solicitud.estado] ?? "neutral"}
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
