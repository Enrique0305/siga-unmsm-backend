import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageInformeConformidadPagoOut } from "@/lib/api/generated/model/pageInformeConformidadPagoOut";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";

const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "neutral" | "warning" | "success" | "danger"> = {
  ENVIADO: "neutral",
  RECIBIDO: "warning",
  EN_PROCESO_DE_PAGO: "warning",
  PAGADO: "success",
  DEVUELTO: "danger",
};

export default async function InformesConformidadPage({
  searchParams,
}: PageProps<"/conformidad">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const [ordenesCompra, data] = await Promise.all([
    serverFetch<PageOrdenCompraOut>("/ordenes-compra?page_size=100"),
    serverFetch<PageInformeConformidadPagoOut>(`/informes-conformidad-pago?${query.toString()}`),
  ]);

  const numeroOc = new Map(ordenesCompra.items.map((oc) => [oc.orden_compra_id, oc.numero_oc]));

  return (
    <div className="space-y-4">
      <SelectFilter
        paramName="estado"
        label="Estado"
        options={[
          { value: "", label: "Todos" },
          { value: "ENVIADO", label: "Enviado" },
          { value: "RECIBIDO", label: "Recibido" },
          { value: "EN_PROCESO_DE_PAGO", label: "En proceso de pago" },
          { value: "PAGADO", label: "Pagado" },
          { value: "DEVUELTO", label: "Devuelto" },
        ]}
      />

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° informe</th>
              <th className="px-4 py-3 font-medium">Orden de compra</th>
              <th className="px-4 py-3 font-medium">Monto conforme</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay informes de conformidad para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((informe) => (
              <tr key={informe.informe_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/conformidad/${informe.informe_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {informe.numero_informe}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {numeroOc.get(informe.orden_compra_id) ?? `#${informe.orden_compra_id}`}
                </td>
                <td className="px-4 py-3">S/ {informe.monto_conforme_total.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={informe.estado}
                    variant={ESTADO_VARIANT[informe.estado] ?? "neutral"}
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
