import { EliminarParametroSistemaButton } from "@/components/administracion/EliminarParametroSistemaButton";
import { ParametroSistemaForm } from "@/components/administracion/ParametroSistemaForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { ParametroSistemaOut } from "@/lib/api/generated/model/parametroSistemaOut";

export default async function ParametrosSistemaPage() {
  const parametros = await serverFetch<ParametroSistemaOut[]>("/parametros-sistema");

  return (
    <div className="space-y-4">
      <ParametroSistemaForm />

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Clave</th>
              <th className="px-4 py-3 font-medium">Valor</th>
              <th className="px-4 py-3 font-medium">Descripción</th>
              <th className="px-4 py-3 font-medium">Actualizado</th>
              <th className="px-4 py-3 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {parametros.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  No hay parámetros configurados — el sistema usa sus valores por defecto.
                </td>
              </tr>
            )}
            {parametros.map((parametro) => (
              <tr key={parametro.clave} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 font-mono text-xs">{parametro.clave}</td>
                <td className="px-4 py-3">{parametro.valor}</td>
                <td className="px-4 py-3 text-text-secondary">{parametro.descripcion ?? "—"}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {new Date(parametro.actualizado_en).toLocaleString("es-PE")}
                </td>
                <td className="px-4 py-3">
                  <EliminarParametroSistemaButton clave={parametro.clave} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
