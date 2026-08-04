import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageGuiaRemisionListOut } from "@/lib/api/generated/model/pageGuiaRemisionListOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  PENDIENTE: "neutral",
  PARCIAL: "warning",
  CONFORME: "success",
  OBSERVADO: "danger",
  SUBSANADO: "warning",
  CERRADO: "neutral",
  PENALIZADO: "danger",
};

export default async function GuiasRemisionPage({
  searchParams,
}: PageProps<"/compras/guias">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageGuiaRemisionListOut>(`/guias-remision?${query.toString()}`),
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
            { value: "PENDIENTE", label: "Pendiente" },
            { value: "PARCIAL", label: "Parcial" },
            { value: "CONFORME", label: "Conforme" },
            { value: "OBSERVADO", label: "Observado" },
            { value: "SUBSANADO", label: "Subsanado" },
            { value: "CERRADO", label: "Cerrado" },
            { value: "PENALIZADO", label: "Penalizado" },
          ]}
        />
        {puedeEditar && (
          <Link
            href="/compras/guias/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva guía de remisión
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° guía</th>
              <th className="px-4 py-3 font-medium">Proveedor</th>
              <th className="px-4 py-3 font-medium">Almacén destino</th>
              <th className="px-4 py-3 font-medium">Fecha entrega</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay guías de remisión para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((guia) => (
              <tr key={guia.guia_remision_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/compras/guias/${guia.guia_remision_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {guia.numero_guia}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">{guia.proveedor_razon_social}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {guia.almacen_destino_codigo} — {guia.almacen_destino_nombre}
                </td>
                <td className="px-4 py-3 text-text-secondary">{guia.fecha_entrega}</td>
                <td className="px-4 py-3">
                  <Badge label={guia.estado} variant={ESTADO_VARIANT[guia.estado] ?? "neutral"} />
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
