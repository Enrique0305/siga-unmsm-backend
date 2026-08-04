import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageUsuarioOut } from "@/lib/api/generated/model/pageUsuarioOut";

const PAGE_SIZE = 20;

export default async function AdministracionUsuariosPage({
  searchParams,
}: PageProps<"/administracion">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;

  const data = await serverFetch<PageUsuarioOut>(
    `/usuarios?page=${page}&page_size=${PAGE_SIZE}`,
  );

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Link
          href="/administracion/nuevo"
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Nuevo usuario
        </Link>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Nombre</th>
              <th className="px-4 py-3 font-medium">Correo</th>
              <th className="px-4 py-3 font-medium">Rol</th>
              <th className="px-4 py-3 font-medium">Estado</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay usuarios para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((usuario) => (
              <tr key={usuario.usuario_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  {usuario.nombres} {usuario.apellidos}
                </td>
                <td className="px-4 py-3 text-text-secondary">{usuario.correo}</td>
                <td className="px-4 py-3">{usuario.rol.nombre}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={usuario.estado}
                    variant={usuario.estado === "ACTIVO" ? "success" : "neutral"}
                  />
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/administracion/${usuario.usuario_id}/editar`}
                    className="text-primary hover:underline"
                  >
                    Editar
                  </Link>
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
