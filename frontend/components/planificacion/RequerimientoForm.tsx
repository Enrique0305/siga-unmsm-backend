"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { UnidadMedida } from "@/components/catalogo/RecetaForm";
import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearRequerimientoApiV1RequerimientosAnualesPost } from "@/lib/api/generated/endpoints/requerimiento-anual-de-insumos/requerimiento-anual-de-insumos";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";
import type { RacionAnualOut } from "@/lib/api/generated/model/racionAnualOut";
import type { RequerimientoAnualDetalleIn } from "@/lib/api/generated/model/requerimientoAnualDetalleIn";

function filaVacia(productoId: number, unidadId: number): RequerimientoAnualDetalleIn {
  return {
    producto_id: productoId,
    cantidad_estimada_anual: 0,
    unidad_id: unidadId,
    presupuesto_referencial: null,
  };
}

export function RequerimientoForm({
  raciones,
  productos,
  unidades,
}: {
  raciones: RacionAnualOut[];
  productos: ProductoOut[];
  unidades: UnidadMedida[];
}) {
  const router = useRouter();
  const crear = useCrearRequerimientoApiV1RequerimientosAnualesPost();

  const [racionAnualId, setRacionAnualId] = useState<number | string>(
    raciones[0]?.racion_anual_id ?? "",
  );
  const [presupuestoTotal, setPresupuestoTotal] = useState("");
  const [detalle, setDetalle] = useState<RequerimientoAnualDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarFila() {
    if (productos.length === 0 || unidades.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(productos[0].producto_id, unidades[0].unidad_id)]);
  }

  function actualizarFila(index: number, patch: Partial<RequerimientoAnualDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarFila(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de detalle.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        racion_anual_id: Number(racionAnualId),
        presupuesto_referencial_total: presupuestoTotal ? Number(presupuestoTotal) : null,
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/planificacion/requerimientos/${response.data.requerimiento_anual_id}`);
    router.refresh();
  }

  if (raciones.length === 0 || productos.length === 0 || unidades.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una ración anual, un producto del catálogo
        logístico y una unidad de medida para crear un requerimiento.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-3xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="racion_anual_id" className="text-sm font-medium">
            Ración anual
          </label>
          <select
            id="racion_anual_id"
            value={racionAnualId}
            onChange={(event) => setRacionAnualId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {raciones.map((racion) => (
              <option key={racion.racion_anual_id} value={racion.racion_anual_id}>
                {racion.anio} — #{racion.racion_anual_id} ({racion.estado})
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="presupuesto_total" className="text-sm font-medium">
            Presupuesto referencial total (opcional)
          </label>
          <input
            id="presupuesto_total"
            type="number"
            min="0"
            step="0.01"
            value={presupuestoTotal}
            onChange={(event) => setPresupuestoTotal(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            Detalle <span className="text-danger">*</span>
          </span>
          <button
            type="button"
            onClick={agregarFila}
            className="text-sm text-primary hover:underline"
          >
            + Agregar línea
          </button>
        </div>
        {detalle.length === 0 && (
          <p className="text-xs text-text-secondary">Se necesita al menos una línea.</p>
        )}
        {detalle.map((fila, index) => (
          <div
            key={index}
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-6 sm:items-end"
          >
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs text-text-secondary">Producto</label>
              <select
                value={fila.producto_id}
                onChange={(event) => actualizarFila(index, { producto_id: Number(event.target.value) })}
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              >
                {productos.map((producto) => (
                  <option key={producto.producto_id} value={producto.producto_id}>
                    {producto.codigo} — {producto.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cantidad anual</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_estimada_anual}
                onChange={(event) =>
                  actualizarFila(index, { cantidad_estimada_anual: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Unidad</label>
              <select
                value={fila.unidad_id}
                onChange={(event) => actualizarFila(index, { unidad_id: Number(event.target.value) })}
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              >
                {unidades.map((unidad) => (
                  <option key={unidad.unidad_id} value={unidad.unidad_id}>
                    {unidad.codigo}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Presupuesto (opcional)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={fila.presupuesto_referencial ?? ""}
                onChange={(event) =>
                  actualizarFila(index, {
                    presupuesto_referencial: event.target.value ? Number(event.target.value) : null,
                  })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => quitarFila(index)}
              className="text-sm text-danger hover:underline"
            >
              Quitar
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Creando..." : "Crear requerimiento"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/planificacion/requerimientos")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
