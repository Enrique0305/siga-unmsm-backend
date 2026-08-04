import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageActaObservacionOut } from "@/lib/api/generated/model/pageActaObservacionOut";

const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  ABIERTA: "warning",
  SUBSANADA: "success",
  RECHAZADA: "danger",
};

export default async function ActasObservacionPage({
  searchParams,
}: PageProps<"/recepcion/actas">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const data = await serverFetch<PageActaObservacionOut>(`/actas-observacion?${query.toString()}`);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SelectFilter
          paramName="estado"
          label="Estado"
          options={[
            { value: "", label: "Todos" },
            { value: "ABIERTA", label: "Abierta" },
            { value: "SUBSANADA", label: "Subsanada" },
            { value: "RECHAZADA", label: "Rechazada" },
          ]}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° acta</th>
              <th className="px-4 py-3 font-medium">Motivo</th>
              <th className="px-4 py-3 font-medium">Plazo subsanación</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay actas de observación para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((acta) => (
              <tr key={acta.acta_observacion_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/recepcion/actas/${acta.acta_observacion_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {acta.numero_acta}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">{acta.motivo}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {acta.plazo_subsanacion}
                  {acta.plazo_vencido && (
                    <span className="ml-2">
                      <Badge label="Plazo vencido" variant="danger" />
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Badge label={acta.estado} variant={ESTADO_VARIANT[acta.estado] ?? "neutral"} />
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
