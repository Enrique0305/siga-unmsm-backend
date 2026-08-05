import Link from "next/link";
import { notFound } from "next/navigation";

import { CambiarEstadoRacion } from "@/components/planificacion/CambiarEstadoRacion";
import { ConsolidarRequerimientoForm } from "@/components/planificacion/ConsolidarRequerimientoForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { PageRequerimientoAnualOut } from "@/lib/api/generated/model/pageRequerimientoAnualOut";
import type { RacionAnualOut } from "@/lib/api/generated/model/racionAnualOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];

export default async function RacionAnualDetailPage({
  params,
}: PageProps<"/planificacion/[id]">) {
  const { id } = await params;

  let racion: RacionAnualOut;
  try {
    racion = await serverFetch<RacionAnualOut>(`/planificacion/raciones-anuales/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, sedes, centros] = await Promise.all([
    getSession(),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const sede = sedes.find((s) => s.sede_id === racion.sede_id);
  const centro = centros.find((c) => c.centro_consumo_id === racion.centro_consumo_id);

  const requerimientos = await serverFetch<PageRequerimientoAnualOut>(
    `/requerimientos-anuales?racion_anual_id=${racion.racion_anual_id}&page_size=1`,
  );
  const requerimientoExistente = requerimientos.items[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Ración anual {racion.anio}
            </h2>
            <p className="text-sm text-text-secondary">
              {sede?.nombre ?? `Sede #${racion.sede_id}`} — {centro?.nombre ?? `Centro #${racion.centro_consumo_id}`}
            </p>
          </div>
          <Badge
            label={racion.estado}
            variant={racion.estado === "APROBADO" ? "success" : "neutral"}
          />
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-text-secondary">Población atendida</dt>
            <dd>{racion.poblacion_atendida}</dd>
          </div>
          <div>
            <dt className="text-text-secondary">Raciones por día</dt>
            <dd>{racion.raciones_dia}</dd>
          </div>
        </dl>

        {puedeEditar && (
          <div className="mt-4">
            <CambiarEstadoRacion racionAnualId={racion.racion_anual_id} estadoActual={racion.estado} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Requerimiento anual (BOM)</h3>
        {requerimientoExistente ? (
          <Link
            href={`/planificacion/requerimientos/${requerimientoExistente.requerimiento_anual_id}`}
            className="text-sm font-medium text-primary hover:underline"
          >
            Ver requerimiento anual generado
          </Link>
        ) : puedeEditar ? (
          <ConsolidarRequerimientoForm racionAnualId={racion.racion_anual_id} />
        ) : (
          <p className="text-sm text-text-secondary">
            Todavía no se generó un requerimiento anual para esta ración.
          </p>
        )}
      </div>
    </div>
  );
}
