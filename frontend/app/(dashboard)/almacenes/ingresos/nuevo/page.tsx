import { IngresoForm } from "@/components/almacenes/IngresoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { InspeccionDetailOut } from "@/lib/api/generated/model/inspeccionDetailOut";
import type { PageGuiaRemisionListOut } from "@/lib/api/generated/model/pageGuiaRemisionListOut";
import type { PageInspeccionOut } from "@/lib/api/generated/model/pageInspeccionOut";
import type { PageUbicacionInternaOut } from "@/lib/api/generated/model/pageUbicacionInternaOut";

export default async function NuevoIngresoAlmacenPage() {
  const [inspecciones, guias, ubicaciones] = await Promise.all([
    serverFetch<PageInspeccionOut>("/inspecciones?page_size=100"),
    serverFetch<PageGuiaRemisionListOut>("/guias-remision?page_size=100"),
    serverFetch<PageUbicacionInternaOut>("/ubicaciones?page_size=100"),
  ]);

  const inspeccionesDetalle = await Promise.all(
    inspecciones.items.map((inspeccion) =>
      serverFetch<InspeccionDetailOut>(`/inspecciones/${inspeccion.inspeccion_id}`),
    ),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo ingreso a almacén</h2>
      <IngresoForm
        inspecciones={inspeccionesDetalle}
        guias={guias.items}
        ubicaciones={ubicaciones.items}
      />
    </div>
  );
}
