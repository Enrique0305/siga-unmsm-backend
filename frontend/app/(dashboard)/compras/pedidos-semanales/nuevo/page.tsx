import { PedidoSemanalForm } from "@/components/compras/PedidoSemanalForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageMenuQuincenalOut } from "@/lib/api/generated/model/pageMenuQuincenalOut";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";

export default async function NuevoPedidoSemanalPage() {
  const [ordenesCompra, menus, almacenes] = await Promise.all([
    serverFetch<PageOrdenCompraOut>("/ordenes-compra?estado=EMITIDA&page_size=100"),
    serverFetch<PageMenuQuincenalOut>("/planificacion/menus-quincenales?page_size=100"),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo pedido semanal</h2>
      <PedidoSemanalForm
        ordenesCompra={ordenesCompra.items}
        menus={menus.items}
        almacenes={almacenes.items}
      />
    </div>
  );
}
