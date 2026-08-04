import { notFound } from "next/navigation";

import { CorregirValoresForm } from "@/components/catalogo/CorregirValoresForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { AlimentoDetailOut } from "@/lib/api/generated/model/alimentoDetailOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];

export default async function AlimentoDetailPage({
  params,
}: PageProps<"/dosificacion/[id]">) {
  const { id } = await params;

  let alimento: AlimentoDetailOut;
  try {
    alimento = await serverFetch<AlimentoDetailOut>(`/alimentos/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const session = await getSession();
  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const vigente = alimento.version_vigente;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {alimento.codigo} — {alimento.nombre}
            </h2>
            <p className="text-sm text-text-secondary">{alimento.categoria.nombre}</p>
          </div>
          <Badge
            label={alimento.estado}
            variant={alimento.estado === "ACTIVO" ? "success" : "neutral"}
          />
        </div>

        {vigente ? (
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-text-secondary">Energía</dt>
              <dd>{vigente.energia_kcal ?? "—"} kcal</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Proteínas</dt>
              <dd>{vigente.proteinas_g ?? "—"} g</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Grasa total</dt>
              <dd>{vigente.grasa_total_g ?? "—"} g</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Carbohidratos</dt>
              <dd>{vigente.carbohidratos_totales_g ?? "—"} g</dd>
            </div>
            <div>
              <dt className="text-text-secondary">Versión vigente</dt>
              <dd>v{vigente.version} ({vigente.fuente})</dd>
            </div>
          </dl>
        ) : (
          <p className="mt-4 text-sm text-text-secondary">
            Sin versión vigente todavía.
          </p>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">
          Historial de versiones
        </h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Versión</th>
              <th className="py-2 font-medium">Fuente</th>
              <th className="py-2 font-medium">Importada</th>
              <th className="py-2 font-medium">Vigente</th>
            </tr>
          </thead>
          <tbody>
            {alimento.versiones.map((version) => (
              <tr
                key={version.alimento_version_id}
                className="border-b border-border/10 last:border-0"
              >
                <td className="py-2">v{version.version}</td>
                <td className="py-2">{version.fuente}</td>
                <td className="py-2">{version.fecha_importacion}</td>
                <td className="py-2">
                  {version.vigente ? (
                    <Badge label="Vigente" variant="success" />
                  ) : (
                    <span className="text-text-secondary">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {puedeEditar && (
        <div className="rounded-lg border border-border/20 bg-white p-6">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Corregir valores nutricionales
          </h3>
          <p className="mb-4 text-xs text-text-secondary">
            RN-25/RN-26: no se sobrescribe la versión actual — esto crea una
            nueva versión vigente y conserva el historial.
          </p>
          <CorregirValoresForm alimentoId={alimento.alimento_id} />
        </div>
      )}
    </div>
  );
}
