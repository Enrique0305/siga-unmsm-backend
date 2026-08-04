import { InspeccionForm } from "@/components/recepcion/InspeccionForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { GuiaRemisionDetailOut } from "@/lib/api/generated/model/guiaRemisionDetailOut";
import type { PageGuiaRemisionListOut } from "@/lib/api/generated/model/pageGuiaRemisionListOut";

export default async function NuevaInspeccionPage() {
  const [pendientes, parciales] = await Promise.all([
    serverFetch<PageGuiaRemisionListOut>("/guias-remision?estado=PENDIENTE&page_size=100"),
    serverFetch<PageGuiaRemisionListOut>("/guias-remision?estado=PARCIAL&page_size=100"),
  ]);

  const candidatas = [...pendientes.items, ...parciales.items];

  const guias = await Promise.all(
    candidatas.map((guia) =>
      serverFetch<GuiaRemisionDetailOut>(`/guias-remision/${guia.guia_remision_id}`),
    ),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva inspección</h2>
      <InspeccionForm guias={guias} />
    </div>
  );
}
