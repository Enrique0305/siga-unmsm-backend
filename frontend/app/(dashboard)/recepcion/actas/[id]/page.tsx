import { notFound } from "next/navigation";

import { AgregarSubsanacionForm } from "@/components/recepcion/AgregarSubsanacionForm";
import { RegistrarReinspeccionForm } from "@/components/recepcion/RegistrarReinspeccionForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { ActaObservacionDetailOut } from "@/lib/api/generated/model/actaObservacionDetailOut";

const ROLES_SUBSANACION = ["ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR"];
const ROLES_INSPECCION = ["ADMIN", "INSPECTOR"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  ABIERTA: "warning",
  SUBSANADA: "success",
  RECHAZADA: "danger",
};

const RESULTADO_VARIANT: Record<string, "success" | "danger" | "neutral"> = {
  CONFORME: "success",
  NO_CONFORME: "danger",
};

export default async function ActaObservacionDetailPage({
  params,
}: PageProps<"/recepcion/actas/[id]">) {
  const { id } = await params;

  let acta: ActaObservacionDetailOut;
  try {
    acta = await serverFetch<ActaObservacionDetailOut>(`/actas-observacion/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const session = await getSession();
  const puedeSubsanar = session ? ROLES_SUBSANACION.includes(session.rol) : false;
  const puedeReinspeccionar = session ? ROLES_INSPECCION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{acta.numero_acta}</h2>
            <p className="mt-1 text-sm text-text-secondary">{acta.motivo}</p>
          </div>
          <div className="flex items-center gap-2">
            {acta.plazo_vencido && <Badge label="Plazo vencido" variant="danger" />}
            <Badge label={acta.estado} variant={ESTADO_VARIANT[acta.estado] ?? "neutral"} />
          </div>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-text-secondary">Cantidad observada</dt>
            <dd>{acta.cantidad_observada}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Plazo de subsanación</dt>
            <dd>{acta.plazo_subsanacion}</dd>
          </div>
        </dl>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Subsanaciones</h3>
        <div className="space-y-3">
          {acta.subsanaciones.length === 0 && (
            <p className="text-sm text-text-secondary">Sin subsanaciones registradas.</p>
          )}
          {acta.subsanaciones.map((subsanacion) => (
            <div key={subsanacion.subsanacion_id} className="rounded-md border border-border/20 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm">Presentada: {subsanacion.fecha_presentacion}</p>
                {subsanacion.resultado_reinspeccion ? (
                  <Badge
                    label={subsanacion.resultado_reinspeccion}
                    variant={RESULTADO_VARIANT[subsanacion.resultado_reinspeccion] ?? "neutral"}
                  />
                ) : (
                  <Badge label="Pendiente de reinspección" variant="neutral" />
                )}
              </div>
              {subsanacion.descripcion && (
                <p className="mt-1 text-sm text-text-secondary">{subsanacion.descripcion}</p>
              )}
              {puedeReinspeccionar &&
                acta.estado === "ABIERTA" &&
                subsanacion.resultado_reinspeccion === null && (
                  <RegistrarReinspeccionForm subsanacionId={subsanacion.subsanacion_id} />
                )}
            </div>
          ))}
        </div>

        {puedeSubsanar && acta.estado === "ABIERTA" && (
          <div className="mt-4">
            <AgregarSubsanacionForm actaObservacionId={acta.acta_observacion_id} />
          </div>
        )}
      </div>
    </div>
  );
}
