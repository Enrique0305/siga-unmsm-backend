import { notFound } from "next/navigation";

import { AnularSolicitudButton } from "@/components/cocina/AnularSolicitudButton";
import { CrearNotaSalidaForm } from "@/components/cocina/CrearNotaSalidaForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { SolicitudCocinaDetailOut } from "@/lib/api/generated/model/solicitudCocinaDetailOut";

const ROLES_SOLICITUD = ["ADMIN", "COCINA"];
const ROLES_NOTA_SALIDA = ["ADMIN", "ALMACENERO"];

const ESTADO_VARIANT: Record<string, "warning" | "success" | "neutral"> = {
  PENDIENTE: "warning",
  DESPACHADA: "success",
  ANULADA: "neutral",
};

export default async function SolicitudCocinaDetailPage({
  params,
}: PageProps<"/cocina/[id]">) {
  const { id } = await params;

  let solicitud: SolicitudCocinaDetailOut;
  try {
    solicitud = await serverFetch<SolicitudCocinaDetailOut>(`/solicitudes-cocina/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, almacen, centrosConsumo] = await Promise.all([
    getSession(),
    serverFetch<AlmacenOut>(`/almacenes/${solicitud.almacen_id}`),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
  ]);

  const centroConsumo = centrosConsumo.find(
    (c) => c.centro_consumo_id === solicitud.centro_consumo_id,
  );

  const puedeAnular = session ? ROLES_SOLICITUD.includes(session.rol) : false;
  const puedeDespachar = session ? ROLES_NOTA_SALIDA.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{solicitud.numero_solicitud}</h2>
            <p className="mt-1 text-sm text-text-secondary">
              {centroConsumo?.nombre ?? `Centro #${solicitud.centro_consumo_id}`} · Almacén{" "}
              {almacen.codigo} — {almacen.nombre}
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              Fecha: {solicitud.creado_en}
            </p>
          </div>
          <Badge
            label={solicitud.estado}
            variant={ESTADO_VARIANT[solicitud.estado] ?? "neutral"}
          />
        </div>
        {puedeAnular && solicitud.estado === "PENDIENTE" && (
          <div className="mt-4">
            <AnularSolicitudButton solicitudCocinaId={solicitud.solicitud_cocina_id} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas solicitadas</h3>
        <table className="mb-4 w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cantidad solicitada</th>
              <th className="py-2 font-medium">Cantidad teórica (BOM)</th>
            </tr>
          </thead>
          <tbody>
            {solicitud.detalle.map((linea) => (
              <tr key={linea.solicitud_cocina_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_solicitada}</td>
                <td className="py-2 text-text-secondary">
                  {linea.cantidad_teorica_bom ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {puedeDespachar && solicitud.estado === "PENDIENTE" && (
          <CrearNotaSalidaForm
            solicitudCocinaId={solicitud.solicitud_cocina_id}
            lineas={solicitud.detalle}
          />
        )}
      </div>
    </div>
  );
}
