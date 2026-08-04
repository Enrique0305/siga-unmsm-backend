import { serverFetch } from "@/lib/api/server-fetch";
import type { CategoriaAlimentoOut } from "@/lib/api/generated/model/categoriaAlimentoOut";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

type UnidadOption = { unidad_id: number; codigo: string; nombre: string };

export default async function CatalogosPage() {
  const [categorias, unidades, sedes, centros] = await Promise.all([
    serverFetch<CategoriaAlimentoOut[]>("/catalogos/categorias-alimento"),
    serverFetch<UnidadOption[]>("/catalogos/unidades-medida"),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
  ]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Categorías de alimento</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <tbody>
              {categorias.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-text-secondary">Sin categorías.</td>
                </tr>
              )}
              {categorias.map((categoria) => (
                <tr key={categoria.categoria_alimento_id} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-2">{categoria.nombre}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Unidades de medida</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">Código</th>
                <th className="px-4 py-2 font-medium">Nombre</th>
              </tr>
            </thead>
            <tbody>
              {unidades.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-center text-text-secondary">
                    Sin unidades.
                  </td>
                </tr>
              )}
              {unidades.map((unidad) => (
                <tr key={unidad.unidad_id} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-2 font-mono text-xs">{unidad.codigo}</td>
                  <td className="px-4 py-2">{unidad.nombre}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Sedes</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium">Dirección</th>
              </tr>
            </thead>
            <tbody>
              {sedes.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-6 text-center text-text-secondary">
                    Sin sedes.
                  </td>
                </tr>
              )}
              {sedes.map((sede) => (
                <tr key={sede.sede_id} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-2">{sede.nombre}</td>
                  <td className="px-4 py-2 text-text-secondary">{sede.direccion ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Centros de consumo</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium">Almacén</th>
                <th className="px-4 py-2 font-medium">Población</th>
              </tr>
            </thead>
            <tbody>
              {centros.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-text-secondary">
                    Sin centros de consumo.
                  </td>
                </tr>
              )}
              {centros.map((centro) => (
                <tr key={centro.centro_consumo_id} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-2">{centro.nombre}</td>
                  <td className="px-4 py-2 text-text-secondary">#{centro.almacen_id}</td>
                  <td className="px-4 py-2">{centro.poblacion_referencia ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
