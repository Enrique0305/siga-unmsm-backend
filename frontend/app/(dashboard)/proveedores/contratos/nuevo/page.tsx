import { ContratoForm } from "@/components/contratos/ContratoForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageProveedorOut } from "@/lib/api/generated/model/pageProveedorOut";
import type { PageRequerimientoAnualOut } from "@/lib/api/generated/model/pageRequerimientoAnualOut";

const ESTADOS_HABILITADOS = new Set(["APROBADO", "VIGENTE"]);

export default async function NuevoContratoPage() {
  const [proveedores, requerimientosAprobados, requerimientosVigentes] = await Promise.all([
    serverFetch<PageProveedorOut>("/proveedores?estado=ACTIVO&page_size=100"),
    serverFetch<PageRequerimientoAnualOut>(
      "/requerimientos-anuales?estado=APROBADO&page_size=100",
    ),
    serverFetch<PageRequerimientoAnualOut>(
      "/requerimientos-anuales?estado=VIGENTE&page_size=100",
    ),
  ]);

  const requerimientos = [...requerimientosAprobados.items, ...requerimientosVigentes.items].filter(
    (requerimiento) => ESTADOS_HABILITADOS.has(requerimiento.estado),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo contrato</h2>
      <ContratoForm proveedores={proveedores.items} requerimientos={requerimientos} />
    </div>
  );
}
