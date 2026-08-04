import { RecetaForm, type UnidadMedida } from "@/components/catalogo/RecetaForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlimentoListOut } from "@/lib/api/generated/model/pageAlimentoListOut";

export default async function NuevaRecetaPage() {
  const [alimentos, unidades] = await Promise.all([
    serverFetch<PageAlimentoListOut>("/alimentos?page_size=100"),
    serverFetch<UnidadMedida[]>("/catalogos/unidades-medida"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva receta</h2>
      <RecetaForm alimentos={alimentos.items} unidades={unidades} />
    </div>
  );
}
