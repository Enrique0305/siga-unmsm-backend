import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageContratoListOut } from "@/lib/api/generated/model/pageContratoListOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral"> = {
  VIGENTE: "success",
  SUSPENDIDO: "warning",
  CERRADO: "neutral",
};

export default async function ContratosPage({
  searchParams,
}: PageProps<"/proveedores/contratos">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);
  if (buscar) query.set("buscar", buscar);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageContratoListOut>(`/contratos?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por número de contrato..." />
          <SelectFilter
            paramName="estado"
            label="Estado"
            options={[
              { value: "", label: "Todos" },
              { value: "VIGENTE", label: "Vigente" },
              { value: "SUSPENDIDO", label: "Suspendido" },
              { value: "CERRADO", label: "Cerrado" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/proveedores/contratos/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo contrato
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° contrato</th>
              <th className="px-4 py-3 font-medium">Proveedor</th>
              <th className="px-4 py-3 font-medium">Vigencia</th>
              <th className="px-4 py-3 font-medium">Presupuesto</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay contratos para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((contrato) => (
              <tr key={contrato.contrato_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/proveedores/contratos/${contrato.contrato_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {contrato.numero_contrato}
                  </Link>
                </td>
                <td className="px-4 py-3">{contrato.proveedor_razon_social}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {contrato.fecha_inicio} — {contrato.fecha_fin}
                  {contrato.alerta_vigencia && (
                    <span className="ml-2">
                      <Badge label={`Vence en ${contrato.dias_para_vencer} días`} variant="danger" />
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  S/ {contrato.presupuesto_total.toLocaleString("es-PE", { minimumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={contrato.estado}
                    variant={ESTADO_VARIANT[contrato.estado] ?? "neutral"}
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
