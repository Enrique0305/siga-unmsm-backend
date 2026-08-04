import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageRequerimientoAnualOut } from "@/lib/api/generated/model/pageRequerimientoAnualOut";

const ROLES_CREACION = ["ADMIN", "NUTRICION"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral"> = {
  BORRADOR: "neutral",
  EN_REVISION: "warning",
  APROBADO: "warning",
  VIGENTE: "success",
};

export default async function RequerimientosAnualesPage({
  searchParams,
}: PageProps<"/planificacion/requerimientos">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageRequerimientoAnualOut>(`/requerimientos-anuales?${query.toString()}`),
  ]);

  const puedeCrear = session ? ROLES_CREACION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SelectFilter
          paramName="estado"
          label="Estado"
          options={[
            { value: "", label: "Todos" },
            { value: "BORRADOR", label: "Borrador" },
            { value: "EN_REVISION", label: "En revisión" },
            { value: "APROBADO", label: "Aprobado" },
            { value: "VIGENTE", label: "Vigente" },
          ]}
        />
        {puedeCrear && (
          <Link
            href="/planificacion/requerimientos/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo requerimiento
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Ración anual</th>
              <th className="px-4 py-3 font-medium">Versión</th>
              <th className="px-4 py-3 font-medium">Presupuesto referencial</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay requerimientos anuales para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((requerimiento) => (
              <tr
                key={requerimiento.requerimiento_anual_id}
                className="border-b border-border/10 last:border-0"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/planificacion/requerimientos/${requerimiento.requerimiento_anual_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    #{requerimiento.racion_anual_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">v{requerimiento.version}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {requerimiento.presupuesto_referencial_total != null
                    ? `S/ ${requerimiento.presupuesto_referencial_total.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`
                    : "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={requerimiento.estado}
                    variant={ESTADO_VARIANT[requerimiento.estado] ?? "neutral"}
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
