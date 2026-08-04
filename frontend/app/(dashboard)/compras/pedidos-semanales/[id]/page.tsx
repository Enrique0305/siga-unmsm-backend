import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { PedidoSemanalOut } from "@/lib/api/generated/model/pedidoSemanalOut";

export default async function PedidoSemanalDetailPage({
  params,
}: PageProps<"/compras/pedidos-semanales/[id]">) {
  const { id } = await params;

  let pedido: PedidoSemanalOut;
  try {
    pedido = await serverFetch<PedidoSemanalOut>(`/pedidos-semanales/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <div className="rounded-lg border border-border/20 bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {pedido.semana_inicio} — {pedido.semana_fin}
          </h2>
          <p className="text-sm text-text-secondary">
            {pedido.almacen_codigo} — {pedido.almacen_nombre}
          </p>
        </div>
        <Badge label={pedido.estado} variant="neutral" />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-text-secondary">Orden de compra</dt>
          <dd>#{pedido.orden_compra_id}</dd>
        </div>
        <div>
          <dt className="text-text-secondary">Menú quincenal</dt>
          <dd>#{pedido.menu_id}</dd>
        </div>
      </dl>
    </div>
  );
}
