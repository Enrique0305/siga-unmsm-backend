import { notFound } from "next/navigation";

import { CambiarEstadoReceta } from "@/components/catalogo/CambiarEstadoReceta";
import { RecetaAcciones } from "@/components/catalogo/RecetaAcciones";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { RecetaDetailOut } from "@/lib/api/generated/model/recetaDetailOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  BORRADOR: "neutral",
  EN_REVISION: "warning",
  APROBADO: "warning",
  VIGENTE: "success",
  DESCONTINUADO: "danger",
};

export default async function RecetaDetailPage({
  params,
}: PageProps<"/dosificacion/recetas/[id]">) {
  const { id } = await params;

  let receta: RecetaDetailOut;
  try {
    receta = await serverFetch<RecetaDetailOut>(`/recetas/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const session = await getSession();
  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nutricion = receta.valor_nutricional;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {receta.codigo} — {receta.nombre}
            </h2>
            <p className="text-sm text-text-secondary">
              {receta.categoria_preparacion} · v{receta.version}
              {receta.receta_padre_id && ` (deriva de #${receta.receta_padre_id})`}
            </p>
          </div>
          <Badge
            label={receta.estado}
            variant={ESTADO_VARIANT[receta.estado] ?? "neutral"}
          />
        </div>

        {receta.descripcion && (
          <p className="mt-3 text-sm text-text-secondary">{receta.descripcion}</p>
        )}

        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-text-secondary">Raciones base</dt>
            <dd>{receta.numero_raciones_base}</dd>
          </div>
          <div>
            <dt className="text-text-secondary">Porción</dt>
            <dd>{receta.tamano_porcion_g} g</dd>
          </div>
          <div>
            <dt className="text-text-secondary">Rendimiento</dt>
            <dd>{receta.rendimiento_pct}%</dd>
          </div>
          <div>
            <dt className="text-text-secondary">Merma estimada</dt>
            <dd>{receta.merma_estimada_pct}%</dd>
          </div>
        </dl>

        {receta.procedimiento && (
          <p className="mt-4 whitespace-pre-line text-sm text-text-secondary">
            {receta.procedimiento}
          </p>
        )}

        {puedeEditar && (
          <div className="mt-4 space-y-3">
            <CambiarEstadoReceta recetaId={receta.receta_id} estadoActual={receta.estado} />
            <RecetaAcciones recetaId={receta.receta_id} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Ingredientes</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Alimento</th>
              <th className="py-2 font-medium">Cant. bruta</th>
              <th className="py-2 font-medium">Cant. neta</th>
              <th className="py-2 font-medium">Merma</th>
            </tr>
          </thead>
          <tbody>
            {receta.ingredientes.map((ingrediente) => (
              <tr
                key={ingrediente.receta_ingrediente_id}
                className="border-b border-border/10 last:border-0"
              >
                <td className="py-2">
                  {ingrediente.alimento_codigo} — {ingrediente.alimento_nombre}
                </td>
                <td className="py-2">{ingrediente.cantidad_bruta_g} g</td>
                <td className="py-2">{ingrediente.cantidad_neta_g} g</td>
                <td className="py-2">{ingrediente.merma_pct ?? 0}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Valor nutricional</h3>
        {nutricion ? (
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <p className="text-text-secondary">Energía (total / ración)</p>
              <p>
                {nutricion.energia_kcal_total ?? "—"} / {nutricion.energia_kcal_racion ?? "—"} kcal
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Proteínas (total / ración)</p>
              <p>
                {nutricion.proteinas_g_total ?? "—"} / {nutricion.proteinas_g_racion ?? "—"} g
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Grasa total (total / ración)</p>
              <p>
                {nutricion.grasa_total_g_total ?? "—"} / {nutricion.grasa_total_g_racion ?? "—"} g
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Carbohidratos (total / ración)</p>
              <p>
                {nutricion.carbohidratos_g_total ?? "—"} / {nutricion.carbohidratos_g_racion ?? "—"} g
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Fibra (total / ración)</p>
              <p>
                {nutricion.fibra_g_total ?? "—"} / {nutricion.fibra_g_racion ?? "—"} g
              </p>
            </div>
            <div>
              <p className="text-text-secondary">Sodio (total / ración)</p>
              <p>
                {nutricion.sodio_mg_total ?? "—"} / {nutricion.sodio_mg_racion ?? "—"} mg
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-text-secondary">
            Sin cálculo nutricional todavía.
          </p>
        )}
      </div>
    </div>
  );
}
