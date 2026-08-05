"use client";

import { useRouter } from "next/navigation";

import { useEliminarParametroApiV1ParametrosSistemaClaveDelete } from "@/lib/api/generated/endpoints/parámetros-del-sistema/parámetros-del-sistema";

export function EliminarParametroSistemaButton({ clave }: { clave: string }) {
  const router = useRouter();
  const eliminar = useEliminarParametroApiV1ParametrosSistemaClaveDelete();

  async function handleClick() {
    await eliminar.mutateAsync({ clave });
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
