import { PenalidadForm } from "@/components/conformidad/PenalidadForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageOrdenCompraOut } from "@/lib/api/generated/model/pageOrdenCompraOut";

export default async function NuevaPenalidadPage() {
  const ordenesCompra = await serverFetch<PageOrdenCompraOut>("/ordenes-compra?page_size=100");

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva penalidad manual</h2>
      <PenalidadForm ordenesCompra={ordenesCompra.items} />
    </div>
  );
}
