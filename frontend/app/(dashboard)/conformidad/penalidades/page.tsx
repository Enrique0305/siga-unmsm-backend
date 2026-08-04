import Link from "next/link";

import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";
import type { PagePenalidadOut } from "@/lib/api/generated/model/pagePenalidadOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

export default async function PenalidadesPage({
  searchParams,
}: PageProps<"/conformidad/penalidades">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });

  const [session, ordenesCompra, data] = await Promise.all([
    getSession(),
    serverFetch<PageOrdenCompraOut>("/ordenes-compra?page_size=100"),
    serverFetch<PagePenalidadOut>(`/penalidades?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const numeroOc = new Map(ordenesCompra.items.map((oc) => [oc.orden_compra_id, oc.numero_oc]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-text-secondary">
          Las penalidades por observación se generan automáticamente al cerrar
          una orden de compra con actas rechazadas.
        </p>
        {puedeEditar && (
          <Link
            href="/conformidad/penalidades/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva penalidad manual
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Orden de compra</th>
              <th className="px-4 py-3 font-medium">Monto</th>
              <th className="px-4 py-3 font-medium">Motivo</th>
              <th className="px-4 py-3 font-medium">Origen</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay penalidades para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((penalidad) => (
              <tr key={penalidad.penalidad_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/compras/${penalidad.orden_compra_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {numeroOc.get(penalidad.orden_compra_id) ?? `#${penalidad.orden_compra_id}`}
                  </Link>
                </td>
                <td className="px-4 py-3">S/ {penalidad.monto_penalidad.toFixed(2)}</td>
                <td className="px-4 py-3 text-text-secondary">{penalidad.motivo}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {penalidad.acta_observacion_id ? "Automática (acta rechazada)" : "Manual"}
                </td>
                <td className="px-4 py-3 text-text-secondary">{penalidad.creado_en}</td>
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
