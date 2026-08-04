import type { UnidadMedida } from "@/components/catalogo/RecetaForm";
import { RequerimientoForm } from "@/components/planificacion/RequerimientoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";
import type { PageRacionAnualOut } from "@/lib/api/generated/model/pageRacionAnualOut";

export default async function NuevoRequerimientoPage() {
  const [raciones, productos, unidades] = await Promise.all([
    serverFetch<PageRacionAnualOut>("/planificacion/raciones-anuales?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<UnidadMedida[]>("/catalogos/unidades-medida"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo requerimiento anual</h2>
      <RequerimientoForm raciones={raciones.items} productos={productos.items} unidades={unidades} />
    </div>
  );
}
