"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearInspeccionApiV1InspeccionesPost } from "@/lib/api/generated/endpoints/inspección/inspección";
import type { GuiaRemisionDetailOut } from "@/lib/api/generated/model/guiaRemisionDetailOut";
import type { InspeccionDetalleIn } from "@/lib/api/generated/model/inspeccionDetalleIn";

const EPS = 1e-6;

function filaVacia(guiaRemisionDetalleId: number): InspeccionDetalleIn {
  return {
    guia_remision_detalle_id: guiaRemisionDetalleId,
    cantidad_conforme: 0,
    cantidad_observada: 0,
  };
}

export function InspeccionForm({ guias }: { guias: GuiaRemisionDetailOut[] }) {
  const router = useRouter();
  const crear = useCrearInspeccionApiV1InspeccionesPost();

  const [guiaRemisionId, setGuiaRemisionId] = useState<number | string>(
    guias[0]?.guia_remision_id ?? "",
  );
  const [detalle, setDetalle] = useState<InspeccionDetalleIn[]>(() =>
    (guias[0]?.detalle ?? []).map((linea) => filaVacia(linea.guia_remision_detalle_id)),
  );
  const [error, setError] = useState<string | null>(null);

  const guia = useMemo(
    () => guias.find((g) => g.guia_remision_id === Number(guiaRemisionId)),
    [guias, guiaRemisionId],
  );
  const lineasGuia = guia?.detalle ?? [];

  function handleGuiaChange(value: string) {
    setGuiaRemisionId(value);
    const nuevaGuia = guias.find((g) => g.guia_remision_id === Number(value));
    setDetalle((nuevaGuia?.detalle ?? []).map((linea) => filaVacia(linea.guia_remision_detalle_id)));
  }

  function actualizarLinea(index: number, patch: Partial<InspeccionDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarLinea(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de detalle.");
      return;
    }

    for (const fila of detalle) {
      const linea = lineasGuia.find((l) => l.guia_remision_detalle_id === fila.guia_remision_detalle_id);
      if (!linea) continue;
      const suma = fila.cantidad_conforme + fila.cantidad_observada;
      if (Math.abs(suma - linea.cantidad_entregada) > EPS) {
        setError(
          `La línea ${linea.producto_codigo} suma ${suma}, pero la cantidad entregada es ${linea.cantidad_entregada}.`,
        );
        return;
      }
    }

    const response = await crear.mutateAsync({
      data: { guia_remision_id: Number(guiaRemisionId), detalle },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/recepcion/${response.data.inspeccion_id}`);
    router.refresh();
  }

  if (guias.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una guía de remisión pendiente o parcial de
        inspección para registrar una inspección.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-4xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="guia_remision_id" className="text-sm font-medium">
          Guía de remisión
        </label>
        <select
          id="guia_remision_id"
          value={guiaRemisionId}
          onChange={(event) => handleGuiaChange(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {guias.map((g) => (
            <option key={g.guia_remision_id} value={g.guia_remision_id}>
              {g.numero_guia} — {g.proveedor_razon_social} ({g.estado})
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium">
          Detalle <span className="text-danger">*</span>
        </span>
        {lineasGuia.length === 0 && (
          <p className="text-xs text-warning">
            La guía seleccionada no tiene líneas de detalle.
          </p>
        )}
        {detalle.length === 0 && lineasGuia.length > 0 && (
          <p className="text-xs text-text-secondary">Se necesita al menos una línea.</p>
        )}
        {detalle.map((fila, index) => {
          const linea = lineasGuia.find(
            (l) => l.guia_remision_detalle_id === fila.guia_remision_detalle_id,
          );
          return (
            <div
              key={fila.guia_remision_detalle_id}
              className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-5 sm:items-end"
            >
              <div className="sm:col-span-2">
                <p className="text-xs text-text-secondary">Producto</p>
                <p className="text-sm">
                  {linea?.producto_codigo} — {linea?.producto_nombre}
                </p>
                <p className="text-xs text-text-secondary">
                  Entregado: {linea?.cantidad_entregada}
                </p>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Cant. conforme</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={fila.cantidad_conforme}
                  onChange={(event) =>
                    actualizarLinea(index, { cantidad_conforme: Number(event.target.value) })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Cant. observada</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={fila.cantidad_observada}
                  onChange={(event) =>
                    actualizarLinea(index, { cantidad_observada: Number(event.target.value) })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={() => quitarLinea(index)}
                className="text-sm text-danger hover:underline"
              >
                Quitar
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Registrando..." : "Registrar inspección"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/recepcion")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
