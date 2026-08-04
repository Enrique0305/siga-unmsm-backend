"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearSolicitudApiV1SolicitudesCocinaPost } from "@/lib/api/generated/endpoints/solicitudes-de-cocina/solicitudes-de-cocina";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { MenuDiaOut } from "@/lib/api/generated/model/menuDiaOut";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";
import type { SolicitudCocinaDetalleIn } from "@/lib/api/generated/model/solicitudCocinaDetalleIn";

function filaVacia(productoId: number): SolicitudCocinaDetalleIn {
  return { producto_id: productoId, cantidad_solicitada: 0 };
}

export function SolicitudCocinaForm({
  centrosConsumo,
  menuDias,
  productos,
}: {
  centrosConsumo: CentroConsumoOut[];
  menuDias: MenuDiaOut[];
  productos: ProductoOut[];
}) {
  const router = useRouter();
  const crear = useCrearSolicitudApiV1SolicitudesCocinaPost();

  const [numeroSolicitud, setNumeroSolicitud] = useState("");
  const [centroConsumoId, setCentroConsumoId] = useState<number | string>(
    centrosConsumo[0]?.centro_consumo_id ?? "",
  );
  const [menuDiaId, setMenuDiaId] = useState<number | string>(menuDias[0]?.menu_dia_id ?? "");
  const [detalle, setDetalle] = useState<SolicitudCocinaDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarLinea() {
    if (productos.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(productos[0].producto_id)]);
  }

  function actualizarLinea(index: number, patch: Partial<SolicitudCocinaDetalleIn>) {
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

    const response = await crear.mutateAsync({
      data: {
        numero_solicitud: numeroSolicitud,
        centro_consumo_id: Number(centroConsumoId),
        menu_dia_id: Number(menuDiaId),
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/cocina/${response.data.solicitud_cocina_id}`);
    router.refresh();
  }

  if (centrosConsumo.length === 0 || menuDias.length === 0 || productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un centro de consumo, un día de menú y un
        producto para registrar una solicitud de cocina.
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

      <div className="space-y-1">
        <label htmlFor="numero_solicitud" className="text-sm font-medium">
          N° de solicitud
        </label>
        <input
          id="numero_solicitud"
          value={numeroSolicitud}
          onChange={(event) => setNumeroSolicitud(event.target.value)}
          required
          maxLength={40}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="centro_consumo_id" className="text-sm font-medium">
            Centro de consumo
          </label>
          <select
            id="centro_consumo_id"
            value={centroConsumoId}
            onChange={(event) => setCentroConsumoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {centrosConsumo.map((c) => (
              <option key={c.centro_consumo_id} value={c.centro_consumo_id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="menu_dia_id" className="text-sm font-medium">
            Día de menú
          </label>
          <select
            id="menu_dia_id"
            value={menuDiaId}
            onChange={(event) => setMenuDiaId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {menuDias.map((d) => (
              <option key={d.menu_dia_id} value={d.menu_dia_id}>
                {d.fecha} — {d.tipo_servicio}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            Detalle <span className="text-danger">*</span>
          </span>
          <button
            type="button"
            onClick={agregarLinea}
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
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-4 sm:items-end"
          >
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs text-text-secondary">Producto</label>
              <select
                value={fila.producto_id}
                onChange={(event) =>
                  actualizarLinea(index, { producto_id: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              >
                {productos.map((p) => (
                  <option key={p.producto_id} value={p.producto_id}>
                    {p.codigo} — {p.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cant. solicitada</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_solicitada}
                onChange={(event) =>
                  actualizarLinea(index, { cantidad_solicitada: Number(event.target.value) })
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
        ))}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Registrando..." : "Registrar solicitud"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/cocina")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
