import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageContratoListOut } from "@/lib/api/generated/model/pageContratoListOut";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  EMITIDA: "success",
  ANULADA: "neutral",
  CERRADO: "neutral",
  PENALIZADO: "danger",
};

export default async function OrdenesCompraPage({
  searchParams,
}: PageProps<"/compras">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);
  if (buscar) query.set("buscar", buscar);

  const [session, data, contratos] = await Promise.all([
    getSession(),
    serverFetch<PageOrdenCompraOut>(`/ordenes-compra?${query.toString()}`),
    serverFetch<PageContratoListOut>("/contratos?page_size=100"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const numeroContrato = new Map(contratos.items.map((c) => [c.contrato_id, c.numero_contrato]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por número de OC..." />
          <SelectFilter
            paramName="estado"
            label="Estado"
            options={[
              { value: "", label: "Todos" },
              { value: "EMITIDA", label: "Emitida" },
              { value: "ANULADA", label: "Anulada" },
              { value: "CERRADO", label: "Cerrado" },
              { value: "PENALIZADO", label: "Penalizado" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/compras/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva orden de compra
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° OC</th>
              <th className="px-4 py-3 font-medium">Contrato</th>
              <th className="px-4 py-3 font-medium">Periodo</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay órdenes de compra para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((oc) => (
              <tr key={oc.orden_compra_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/compras/${oc.orden_compra_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {oc.numero_oc}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {numeroContrato.get(oc.contrato_id) ?? `#${oc.contrato_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">{oc.periodo_mes}</td>
                <td className="px-4 py-3">
                  <Badge label={oc.estado} variant={ESTADO_VARIANT[oc.estado] ?? "neutral"} />
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
