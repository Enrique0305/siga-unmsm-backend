"use client";

import { useRouter } from "next/navigation";

import { useEliminarParametroApiV1ParametrosStockAlmacenIdProductoIdDelete } from "@/lib/api/generated/endpoints/parámetros-de-stock-por-almacén/parámetros-de-stock-por-almacén";

export function EliminarParametroButton({
  almacenId,
  productoId,
}: {
  almacenId: number;
  productoId: number;
}) {
  const router = useRouter();
  const eliminar = useEliminarParametroApiV1ParametrosStockAlmacenIdProductoIdDelete();

  async function handleClick() {
    await eliminar.mutateAsync({ almacenId, productoId });
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={eliminar.isPending}
      className="text-sm font-medium text-danger hover:underline disabled:opacity-60"
    >
      {eliminar.isPending ? "Eliminando..." : "Eliminar"}
    </button>
  );
}
