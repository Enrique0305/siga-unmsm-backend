"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearIngresoApiV1IngresosAlmacenPost } from "@/lib/api/generated/endpoints/ingresos-a-almacén/ingresos-a-almacén";
import type { GuiaRemisionListOut } from "@/lib/api/generated/model/guiaRemisionListOut";
import type { IngresoAlmacenDetalleIn } from "@/lib/api/generated/model/ingresoAlmacenDetalleIn";
import type { InspeccionDetailOut } from "@/lib/api/generated/model/inspeccionDetailOut";
import type { UbicacionInternaOut } from "@/lib/api/generated/model/ubicacionInternaOut";

function filasIniciales(inspeccion?: InspeccionDetailOut): IngresoAlmacenDetalleIn[] {
  return (inspeccion?.detalle ?? [])
    .filter((linea) => linea.cantidad_conforme > 0)
    .map((linea) => ({
      inspeccion_detalle_id: linea.inspeccion_detalle_id,
      cantidad_ingresada: linea.cantidad_conforme,
      ubicacion_id: null,
    }));
}

export function IngresoForm({
  inspecciones,
  guias,
  ubicaciones,
}: {
  inspecciones: InspeccionDetailOut[];
  guias: GuiaRemisionListOut[];
  ubicaciones: UbicacionInternaOut[];
}) {
  const router = useRouter();
  const crear = useCrearIngresoApiV1IngresosAlmacenPost();

  const [numeroIngreso, setNumeroIngreso] = useState("");
  const [inspeccionId, setInspeccionId] = useState<number | string>(
    inspecciones[0]?.inspeccion_id ?? "",
  );
  const [detalle, setDetalle] = useState<IngresoAlmacenDetalleIn[]>(() =>
    filasIniciales(inspecciones[0]),
  );
  const [error, setError] = useState<string | null>(null);

  const inspeccion = useMemo(
    () => inspecciones.find((i) => i.inspeccion_id === Number(inspeccionId)),
    [inspecciones, inspeccionId],
  );
  const guia = useMemo(
    () => guias.find((g) => g.guia_remision_id === inspeccion?.guia_remision_id),
    [guias, inspeccion],
  );
  const ubicacionesDelAlmacen = useMemo(
    () => ubicaciones.filter((u) => u.almacen_id === guia?.almacen_destino_id),
    [ubicaciones, guia],
  );

  function handleInspeccionChange(value: string) {
    setInspeccionId(value);
    const nuevaInspeccion = inspecciones.find((i) => i.inspeccion_id === Number(value));
    setDetalle(filasIniciales(nuevaInspeccion));
  }

  function actualizarLinea(index: number, patch: Partial<IngresoAlmacenDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarLinea(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!inspeccion) {
      setError("Selecciona una inspección.");
      return;
    }
    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de detalle.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        numero_ingreso: numeroIngreso,
        guia_remision_id: inspeccion.guia_remision_id,
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/almacenes/ingresos/${response.data.ingreso_almacen_id}`);
    router.refresh();
  }

  if (inspecciones.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una inspección con líneas conformes para registrar
        un ingreso a almacén.
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="numero_ingreso" className="text-sm font-medium">
            N° de ingreso
          </label>
          <input
            id="numero_ingreso"
            value={numeroIngreso}
            onChange={(event) => setNumeroIngreso(event.target.value)}
            required
            maxLength={40}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="inspeccion_id" className="text-sm font-medium">
            Inspección
          </label>
          <select
            id="inspeccion_id"
            value={inspeccionId}
            onChange={(event) => handleInspeccionChange(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {inspecciones.map((i) => (
              <option key={i.inspeccion_id} value={i.inspeccion_id}>
                Inspección #{i.inspeccion_id} — Guía{" "}
                {guias.find((g) => g.guia_remision_id === i.guia_remision_id)?.numero_guia ??
                  `#${i.guia_remision_id}`}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium">
          Detalle <span className="text-danger">*</span>
        </span>
        {detalle.length === 0 && (
          <p className="text-xs text-warning">
            Esta inspección no tiene líneas conformes disponibles para ingresar.
          </p>
        )}
        {detalle.map((fila, index) => {
          const linea = inspeccion?.detalle.find(
            (l) => l.inspeccion_detalle_id === fila.inspeccion_detalle_id,
          );
          return (
            <div
              key={fila.inspeccion_detalle_id}
              className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-5 sm:items-end"
            >
              <div className="sm:col-span-2">
                <p className="text-xs text-text-secondary">Producto</p>
                <p className="text-sm">
                  {linea?.producto_codigo} — {linea?.producto_nombre}
                </p>
                <p className="text-xs text-text-secondary">
                  Conforme: {linea?.cantidad_conforme}
                </p>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Cant. ingresada</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={fila.cantidad_ingresada}
                  onChange={(event) =>
                    actualizarLinea(index, { cantidad_ingresada: Number(event.target.value) })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Ubicación (opcional)</label>
                <select
                  value={fila.ubicacion_id ?? ""}
                  onChange={(event) =>
                    actualizarLinea(index, {
                      ubicacion_id: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="">Sin ubicación</option>
                  {ubicacionesDelAlmacen.map((u) => (
                    <option key={u.ubicacion_id} value={u.ubicacion_id}>
                      {u.zona}
                      {u.estante ? ` / ${u.estante}` : ""}
                    </option>
                  ))}
                </select>
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
          {crear.isPending ? "Registrando..." : "Registrar ingreso"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/almacenes/ingresos")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
