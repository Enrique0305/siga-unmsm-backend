import { RacionAnualForm } from "@/components/planificacion/RacionAnualForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export default async function NuevaRacionAnualPage() {
  const [sedes, centros] = await Promise.all([
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva ración anual</h2>
      <RacionAnualForm sedes={sedes} centros={centros} />
    </div>
  );
}
