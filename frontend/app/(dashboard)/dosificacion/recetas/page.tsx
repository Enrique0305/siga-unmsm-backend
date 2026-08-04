import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageRecetaOut } from "@/lib/api/generated/model/pageRecetaOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];
const PAGE_SIZE = 20;

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  BORRADOR: "neutral",
  EN_REVISION: "warning",
  APROBADO: "warning",
  VIGENTE: "success",
  DESCONTINUADO: "danger",
};

export default async function RecetasPage({
  searchParams,
}: PageProps<"/dosificacion/recetas">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (estado) query.set("estado", estado);
  if (buscar) query.set("buscar", buscar);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageRecetaOut>(`/recetas?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por código o nombre..." />
          <SelectFilter
            paramName="estado"
            label="Estado"
            options={[
              { value: "", label: "Todos" },
              { value: "BORRADOR", label: "Borrador" },
              { value: "EN_REVISION", label: "En revisión" },
              { value: "APROBADO", label: "Aprobado" },
              { value: "VIGENTE", label: "Vigente" },
              { value: "DESCONTINUADO", label: "Descontinuado" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/dosificacion/recetas/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nueva receta
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Código</th>
              <th className="px-4 py-3 font-medium">Nombre</th>
              <th className="px-4 py-3 font-medium">Categoría</th>
              <th className="px-4 py-3 font-medium">Versión</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay recetas para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((receta) => (
              <tr key={receta.receta_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/dosificacion/recetas/${receta.receta_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {receta.codigo}
                  </Link>
                </td>
                <td className="px-4 py-3">{receta.nombre}</td>
                <td className="px-4 py-3 text-text-secondary">{receta.categoria_preparacion}</td>
                <td className="px-4 py-3 text-text-secondary">v{receta.version}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={receta.estado}
                    variant={ESTADO_VARIANT[receta.estado] ?? "neutral"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4">
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} />
        </div>
      </div>
    </div>
  );
}
