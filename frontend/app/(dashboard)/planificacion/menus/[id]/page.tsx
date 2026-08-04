import Link from "next/link";
import { notFound } from "next/navigation";

import { AgregarDiaForm } from "@/components/planificacion/AgregarDiaForm";
import { CambiarEstadoMenu } from "@/components/planificacion/CambiarEstadoMenu";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { MenuQuincenalDetailOut } from "@/lib/api/generated/model/menuQuincenalDetailOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  BORRADOR: "neutral",
  EN_REVISION: "warning",
  APROBADO: "warning",
  VIGENTE: "success",
  HISTORICO: "danger",
};

export default async function MenuQuincenalDetailPage({
  params,
}: PageProps<"/planificacion/menus/[id]">) {
  const { id } = await params;

  let menu: MenuQuincenalDetailOut;
  try {
    menu = await serverFetch<MenuQuincenalDetailOut>(`/planificacion/menus-quincenales/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const session = await getSession();
  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {menu.quincena_inicio} — {menu.quincena_fin}
            </h2>
            <p className="text-sm text-text-secondary">
              Ración anual #{menu.racion_anual_id} · v{menu.version}
              {menu.aprobado_en && ` · aprobado el ${menu.aprobado_en.slice(0, 10)}`}
            </p>
          </div>
          <Badge label={menu.estado} variant={ESTADO_VARIANT[menu.estado] ?? "neutral"} />
        </div>

        {puedeEditar && (
          <div className="mt-4">
            <CambiarEstadoMenu menuId={menu.menu_id} estadoActual={menu.estado} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Días del menú</h3>
        {menu.dias.length === 0 ? (
          <p className="mb-4 text-sm text-text-secondary">Sin días agregados todavía.</p>
        ) : (
          <table className="mb-4 w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="py-2 font-medium">Fecha</th>
                <th className="py-2 font-medium">Servicio</th>
                <th className="py-2 font-medium">Raciones</th>
                <th className="py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {menu.dias.map((dia) => (
                <tr key={dia.menu_dia_id} className="border-b border-border/10 last:border-0">
                  <td className="py-2">{dia.fecha}</td>
                  <td className="py-2">{dia.tipo_servicio}</td>
                  <td className="py-2">{dia.raciones_programadas}</td>
                  <td className="py-2 text-right">
                    <Link
                      href={`/planificacion/dias/${dia.menu_dia_id}`}
                      className="text-primary hover:underline"
                    >
                      Ver platos
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {puedeEditar && <AgregarDiaForm menuId={menu.menu_id} />}
      </div>
    </div>
  );
}
