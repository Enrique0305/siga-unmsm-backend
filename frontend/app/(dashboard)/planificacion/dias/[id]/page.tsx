import Link from "next/link";
import { notFound } from "next/navigation";

import { AgregarPlatoForm } from "@/components/planificacion/AgregarPlatoForm";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { MenuDiaDetailOut } from "@/lib/api/generated/model/menuDiaDetailOut";
import type { PageRecetaOut } from "@/lib/api/generated/model/pageRecetaOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];

export default async function MenuDiaDetailPage({
  params,
}: PageProps<"/planificacion/dias/[id]">) {
  const { id } = await params;

  let dia: MenuDiaDetailOut;
  try {
    dia = await serverFetch<MenuDiaDetailOut>(`/planificacion/dias/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, recetasVigentes] = await Promise.all([
    getSession(),
    serverFetch<PageRecetaOut>("/recetas?estado=VIGENTE&page_size=100"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {dia.fecha} — {dia.tipo_servicio}
            </h2>
            <p className="text-sm text-text-secondary">
              {dia.raciones_programadas} raciones programadas
            </p>
          </div>
          <Link
            href={`/dosificacion/calcular?menu_dia_id=${dia.menu_dia_id}`}
            className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface"
          >
            Calcular dosificación
          </Link>
        </div>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Platos</h3>
        {dia.platos.length === 0 ? (
          <p className="mb-4 text-sm text-text-secondary">Sin platos agregados todavía.</p>
        ) : (
          <table className="mb-4 w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="py-2 font-medium">Receta</th>
                <th className="py-2 font-medium">Raciones (override)</th>
              </tr>
            </thead>
            <tbody>
              {dia.platos.map((plato) => (
                <tr key={plato.plato_id} className="border-b border-border/10 last:border-0">
                  <td className="py-2">{plato.receta_nombre}</td>
                  <td className="py-2 text-text-secondary">
                    {plato.raciones_override ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {puedeEditar && (
          <AgregarPlatoForm menuDiaId={dia.menu_dia_id} recetas={recetasVigentes.items} />
        )}
      </div>
    </div>
  );
}
