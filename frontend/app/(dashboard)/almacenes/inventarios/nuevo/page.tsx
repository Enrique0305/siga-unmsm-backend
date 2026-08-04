import { InventarioFisicoForm } from "@/components/almacenes/InventarioFisicoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

export default async function NuevoInventarioFisicoPage() {
  const [almacenes, productos] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo inventario físico</h2>
      <InventarioFisicoForm almacenes={almacenes.items} productos={productos.items} />
    </div>
  );
}
