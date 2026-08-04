import { AlimentoForm } from "@/components/catalogo/AlimentoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { CategoriaAlimentoOut } from "@/lib/api/generated/model/categoriaAlimentoOut";

export default async function NuevoAlimentoPage() {
  const categorias = await serverFetch<CategoriaAlimentoOut[]>(
    "/catalogos/categorias-alimento",
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo alimento</h2>
      <AlimentoForm categorias={categorias} />
    </div>
  );
}
