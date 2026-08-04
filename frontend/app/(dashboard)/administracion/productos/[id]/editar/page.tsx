import { notFound } from "next/navigation";

import { ProductoForm } from "@/components/administracion/ProductoForm";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

type UnidadOption = { unidad_id: number; codigo: string; nombre: string };

export default async function EditarProductoPage({
  params,
}: PageProps<"/administracion/productos/[id]/editar">) {
  const { id } = await params;

  let producto: ProductoOut;
  try {
    producto = await serverFetch<ProductoOut>(`/productos/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const unidades = await serverFetch<UnidadOption[]>("/catalogos/unidades-medida");

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">
        Editar producto — {producto.nombre}
      </h2>
      <ProductoForm mode="edit" producto={producto} unidades={unidades} />
    </div>
  );
}
