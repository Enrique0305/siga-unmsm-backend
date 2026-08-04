import Link from "next/link";

import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageNotaSalidaOut } from "@/lib/api/generated/model/pageNotaSalidaOut";
import type { PageSolicitudCocinaOut } from "@/lib/api/generated/model/pageSolicitudCocinaOut";

const PAGE_SIZE = 20;

export default async function NotasSalidaPage({
  searchParams,
}: PageProps<"/cocina/notas-salida">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);

  const [almacenes, solicitudes, data] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageSolicitudCocinaOut>("/solicitudes-cocina?page_size=100"),
    serverFetch<PageNotaSalidaOut>(`/notas-salida?${query.toString()}`),
  ]);

  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, a.codigo]));
  const numeroSolicitud = new Map(
    solicitudes.items.map((s) => [s.solicitud_cocina_id, s.numero_solicitud]),
  );

  return (
    <div className="space-y-4">
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
              <th className="px-4 py-3 font-medium">N° nota</th>
              <th className="px-4 py-3 font-medium">Solicitud</th>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay notas de salida para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((nota) => (
              <tr key={nota.nota_salida_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/cocina/notas-salida/${nota.nota_salida_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {nota.numero_nota}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {numeroSolicitud.get(nota.solicitud_cocina_id) ?? `#${nota.solicitud_cocina_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(nota.almacen_id) ?? `#${nota.almacen_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">{nota.fecha_salida}</td>
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
