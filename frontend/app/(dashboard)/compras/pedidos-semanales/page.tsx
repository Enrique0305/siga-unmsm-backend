import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PagePedidoSemanalOut } from "@/lib/api/generated/model/pagePedidoSemanalOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL", "NUTRICION"];
const PAGE_SIZE = 20;

export default async function PedidosSemanalesPage({
  searchParams,
}: PageProps<"/compras/pedidos-semanales">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PagePedidoSemanalOut>(
      `/pedidos-semanales?page=${page}&page_size=${PAGE_SIZE}`,
    ),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-end gap-3">
        {puedeEditar && (
          <Link
            href="/compras/pedidos-semanales/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo pedido semanal
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Semana</th>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Orden de compra</th>
              <th className="px-4 py-3 font-medium">Menú</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay pedidos semanales para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((pedido) => (
              <tr key={pedido.pedido_semanal_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/compras/pedidos-semanales/${pedido.pedido_semanal_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {pedido.semana_inicio} — {pedido.semana_fin}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {pedido.almacen_codigo} — {pedido.almacen_nombre}
                </td>
                <td className="px-4 py-3 text-text-secondary">#{pedido.orden_compra_id}</td>
                <td className="px-4 py-3 text-text-secondary">#{pedido.menu_id}</td>
                <td className="px-4 py-3">
                  <Badge label={pedido.estado} variant="neutral" />
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
