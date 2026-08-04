import { GuiaRemisionForm } from "@/components/compras/GuiaRemisionForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { OrdenCompraDetailOut } from "@/lib/api/generated/model/ordenCompraDetailOut";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";
import type { PagePedidoSemanalOut } from "@/lib/api/generated/model/pagePedidoSemanalOut";
import type { PageProveedorOut } from "@/lib/api/generated/model/pageProveedorOut";

export default async function NuevaGuiaRemisionPage() {
  const [proveedores, ordenesCompraEmitidas, pedidosSemanales, almacenes] = await Promise.all([
    serverFetch<PageProveedorOut>("/proveedores?estado=ACTIVO&page_size=100"),
    serverFetch<PageOrdenCompraOut>("/ordenes-compra?estado=EMITIDA&page_size=100"),
    serverFetch<PagePedidoSemanalOut>("/pedidos-semanales?page_size=100"),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
  ]);

  const ordenesCompra = await Promise.all(
    ordenesCompraEmitidas.items.map((oc) =>
      serverFetch<OrdenCompraDetailOut>(`/ordenes-compra/${oc.orden_compra_id}`),
    ),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva guía de remisión</h2>
      <GuiaRemisionForm
        proveedores={proveedores.items}
        ordenesCompra={ordenesCompra}
        pedidosSemanales={pedidosSemanales.items}
        almacenes={almacenes.items}
      />
    </div>
  );
}
