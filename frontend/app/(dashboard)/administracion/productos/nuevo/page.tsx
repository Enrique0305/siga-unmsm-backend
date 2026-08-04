import { ProductoForm } from "@/components/administracion/ProductoForm";
import { serverFetch } from "@/lib/api/server-fetch";

type UnidadOption = { unidad_id: number; codigo: string; nombre: string };

export default async function NuevoProductoPage() {
  const unidades = await serverFetch<UnidadOption[]>("/catalogos/unidades-medida");

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo producto</h2>
      <ProductoForm mode="create" unidades={unidades} />
    </div>
  );
}
