import { OrdenCompraForm } from "@/components/compras/OrdenCompraForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { ContratoDetailOut } from "@/lib/api/generated/model/contratoDetailOut";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageContratoListOut } from "@/lib/api/generated/model/pageContratoListOut";

export default async function NuevaOrdenCompraPage() {
  const [contratosVigentes, almacenes] = await Promise.all([
    serverFetch<PageContratoListOut>("/contratos?estado=VIGENTE&page_size=100"),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
  ]);

  const contratos = await Promise.all(
    contratosVigentes.items.map((contrato) =>
      serverFetch<ContratoDetailOut>(`/contratos/${contrato.contrato_id}`),
    ),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva orden de compra</h2>
      <OrdenCompraForm contratos={contratos} almacenes={almacenes.items} />
    </div>
  );
}
