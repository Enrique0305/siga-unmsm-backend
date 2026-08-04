import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlimentoListOut } from "@/lib/api/generated/model/pageAlimentoListOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION"];
const PAGE_SIZE = 20;

export default async function AlimentosPage({
  searchParams,
}: PageProps<"/dosificacion">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const tipo = typeof params.tipo === "string" ? params.tipo : "";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (tipo) query.set("tipo", tipo);
  if (buscar) query.set("buscar", buscar);

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlimentoListOut>(`/alimentos?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por código o nombre..." />
          <SelectFilter
            paramName="tipo"
            label="Tipo"
            options={[
              { value: "", label: "Todos" },
              { value: "BASE_TABLA", label: "Base de tabla" },
              { value: "PREPARADO_IMPORTADO", label: "Preparado importado" },
              { value: "PREPARACION_INSTITUCIONAL", label: "Preparación institucional" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/dosificacion/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo alimento
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
              <th className="px-4 py-3 font-medium">Energía (kcal/100g)</th>
              <th className="px-4 py-3 font-medium">Estado</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay alimentos para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((alimento) => (
              <tr key={alimento.alimento_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/dosificacion/${alimento.alimento_id}`}
                    className="font-medium text-primary hover:underline"
                  >
                    {alimento.codigo}
                  </Link>
                </td>
                <td className="px-4 py-3">{alimento.nombre}</td>
                <td className="px-4 py-3 text-text-secondary">{alimento.categoria.nombre}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {alimento.version_vigente?.energia_kcal ?? "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={alimento.estado}
                    variant={alimento.estado === "ACTIVO" ? "success" : "neutral"}
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
