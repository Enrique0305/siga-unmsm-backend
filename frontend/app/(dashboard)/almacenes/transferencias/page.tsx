import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageTransferenciaAlmacenOut } from "@/lib/api/generated/model/pageTransferenciaAlmacenOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "warning" | "success" | "danger" | "neutral"> = {
  EN_TRANSITO: "warning",
  RECIBIDA_CONFORME: "success",
  RECIBIDA_CON_DIFERENCIA: "danger",
  ANULADA: "neutral",
};

export default async function TransferenciasPage({
  searchParams,
}: PageProps<"/almacenes/transferencias">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);

  const [session, almacenes, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageTransferenciaAlmacenOut>(`/transferencias?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, a.codigo]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SelectFilter
          paramName="estado"
          label="Estado"
          options={[
            { value: "", label: "Todos" },
            { value: "EN_TRANSITO", label: "En tránsito" },
            { value: "RECIBIDA_CONFORME", label: "Recibida conforme" },
            { value: "RECIBIDA_CON_DIFERENCIA", label: "Recibida con diferencia" },
          ]}
        />
        {puedeEditar && (
          <Link
            href="/almacenes/transferencias/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva transferencia
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">N° transferencia</th>
              <th className="px-4 py-3 font-medium">Origen</th>
              <th className="px-4 py-3 font-medium">Destino</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-secondary">
                  No hay transferencias para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((transferencia) => (
              <tr key={transferencia.transferencia_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/almacenes/transferencias/${transferencia.transferencia_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {transferencia.numero_transferencia}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(transferencia.almacen_origen_id) ??
                    `#${transferencia.almacen_origen_id}`}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(transferencia.almacen_destino_id) ??
                    `#${transferencia.almacen_destino_id}`}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={transferencia.estado}
                    variant={ESTADO_VARIANT[transferencia.estado] ?? "neutral"}
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
