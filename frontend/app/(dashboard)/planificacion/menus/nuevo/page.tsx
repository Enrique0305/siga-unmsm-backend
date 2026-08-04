import { MenuQuincenalForm } from "@/components/planificacion/MenuQuincenalForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageRacionAnualOut } from "@/lib/api/generated/model/pageRacionAnualOut";

export default async function NuevoMenuQuincenalPage() {
  const raciones = await serverFetch<PageRacionAnualOut>(
    "/planificacion/raciones-anuales?page_size=100",
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo menú quincenal</h2>
      <MenuQuincenalForm raciones={raciones.items} />
    </div>
  );
}
