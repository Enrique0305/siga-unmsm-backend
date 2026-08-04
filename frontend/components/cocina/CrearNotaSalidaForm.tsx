"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearNotaSalidaApiV1NotasSalidaPost } from "@/lib/api/generated/endpoints/notas-de-salida/notas-de-salida";
import type { NotaSalidaDetalleIn } from "@/lib/api/generated/model/notaSalidaDetalleIn";
import type { SolicitudCocinaDetalleOut } from "@/lib/api/generated/model/solicitudCocinaDetalleOut";

export function CrearNotaSalidaForm({
  solicitudCocinaId,
  lineas,
}: {
  solicitudCocinaId: number;
  lineas: SolicitudCocinaDetalleOut[];
}) {
  const router = useRouter();
  const crear = useCrearNotaSalidaApiV1NotasSalidaPost();

  const [numeroNota, setNumeroNota] = useState("");
  const [detalle, setDetalle] = useState<NotaSalidaDetalleIn[]>(() =>
    lineas.map((linea) => ({
      solicitud_cocina_detalle_id: linea.solicitud_cocina_detalle_id,
      cantidad_despachada: linea.cantidad_solicitada,
    })),
  );
  const [error, setError] = useState<string | null>(null);

  function actualizarLinea(index: number, patch: Partial<NotaSalidaDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: { numero_nota: numeroNota, solicitud_cocina_id: solicitudCocinaId, detalle },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/cocina/notas-salida/${response.data.nota_salida_id}`);
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-sm font-medium text-foreground">
        Crear nota de salida (cubre todas las líneas de la solicitud)
      </p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="space-y-1">
        <label className="text-xs text-text-secondary">N° de nota</label>
        <input
          value={numeroNota}
          onChange={(event) => setNumeroNota(event.target.value)}
          required
          maxLength={40}
          className="w-full max-w-xs rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
        />
      </div>
      {detalle.map((fila, index) => {
        const linea = lineas.find(
          (l) => l.solicitud_cocina_detalle_id === fila.solicitud_cocina_detalle_id,
        );
        return (
          <div
            key={fila.solicitud_cocina_detalle_id}
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-3 sm:items-end"
          >
            <div>
              <p className="text-xs text-text-secondary">Producto</p>
              <p className="text-sm">
                {linea?.producto_codigo} — {linea?.producto_nombre}
              </p>
              <p className="text-xs text-text-secondary">
                Solicitado: {linea?.cantidad_solicitada}
              </p>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cant. despachada</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_despachada}
                onChange={(event) =>
                  actualizarLinea(index, { cantidad_despachada: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        );
      })}
      <p className="text-xs text-text-secondary">
        Despachar menos de lo solicitado libera igual el 100% de la reserva de esa línea.
      </p>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {crear.isPending ? "Registrando..." : "Registrar nota de salida"}
      </button>
    </form>
  );
}
