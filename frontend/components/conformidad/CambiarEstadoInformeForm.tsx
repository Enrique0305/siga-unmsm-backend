"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoInformeApiV1InformesConformidadPagoInformeIdEstadoPatch } from "@/lib/api/generated/endpoints/informes-de-conformidad-para-pago/informes-de-conformidad-para-pago";

const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  ENVIADO: ["RECIBIDO", "DEVUELTO"],
  RECIBIDO: ["EN_PROCESO_DE_PAGO", "DEVUELTO"],
  EN_PROCESO_DE_PAGO: ["PAGADO", "DEVUELTO"],
  PAGADO: [],
  DEVUELTO: [],
};

const ESTADO_LABEL: Record<string, string> = {
  RECIBIDO: "Marcar como recibido",
  EN_PROCESO_DE_PAGO: "Pasar a proceso de pago",
  PAGADO: "Marcar como pagado",
  DEVUELTO: "Devolver",
};

export function CambiarEstadoInformeForm({
  informeId,
  estadoActual,
}: {
  informeId: number;
  estadoActual: string;
}) {
  const router = useRouter();
  const cambiar = useCambiarEstadoInformeApiV1InformesConformidadPagoInformeIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  const destinos = TRANSICIONES_VALIDAS[estadoActual] ?? [];

  async function handleClick(estado: string) {
    setError(null);
    const response = await cambiar.mutateAsync({ informeId, data: { estado } });

    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.refresh();
  }

  if (destinos.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="flex flex-wrap gap-2">
        {destinos.map((estado) => (
          <button
            key={estado}
            type="button"
            onClick={() => handleClick(estado)}
            disabled={cambiar.isPending}
            className={`rounded-md px-4 py-2 text-sm font-medium disabled:opacity-60 ${
              estado === "DEVUELTO"
                ? "border border-danger/30 text-danger hover:bg-danger/10"
                : "bg-primary text-white hover:bg-primary-hover"
            }`}
          >
            {ESTADO_LABEL[estado] ?? estado}
          </button>
        ))}
      </div>
    </div>
  );
}
