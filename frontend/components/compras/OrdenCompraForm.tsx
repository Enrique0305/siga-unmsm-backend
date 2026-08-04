"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearOrdenCompraApiV1OrdenesCompraPost } from "@/lib/api/generated/endpoints/órdenes-de-compra/órdenes-de-compra";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { ContratoDetailOut } from "@/lib/api/generated/model/contratoDetailOut";
import type { OrdenCompraDetalleIn } from "@/lib/api/generated/model/ordenCompraDetalleIn";
import type { OrdenCompraDistribucionIn } from "@/lib/api/generated/model/ordenCompraDistribucionIn";

const EPS = 1e-6;

function filaVacia(productoContratadoId: number): OrdenCompraDetalleIn {
  return { producto_contratado_id: productoContratadoId, cantidad_solicitada: 0, distribucion: [] };
}

function distribucionVacia(almacenId: number): OrdenCompraDistribucionIn {
  return { almacen_id: almacenId, cantidad_distribuida: 0 };
}

export function OrdenCompraForm({
  contratos,
  almacenes,
}: {
  contratos: ContratoDetailOut[];
  almacenes: AlmacenOut[];
}) {
  const router = useRouter();
  const crear = useCrearOrdenCompraApiV1OrdenesCompraPost();

  const [numeroOc, setNumeroOc] = useState("");
  const [contratoId, setContratoId] = useState<number | string>(
    contratos[0]?.contrato_id ?? "",
  );
  const [periodoMes, setPeriodoMes] = useState("");
  const [detalle, setDetalle] = useState<OrdenCompraDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  const contrato = useMemo(
    () => contratos.find((c) => c.contrato_id === Number(contratoId)),
    [contratos, contratoId],
  );
  const productos = contrato?.productos_contratados ?? [];

  function handleContratoChange(value: string) {
    setContratoId(value);
    setDetalle([]);
  }

  function agregarLinea() {
    if (productos.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(productos[0].producto_contratado_id)]);
  }

  function actualizarLinea(index: number, patch: Partial<OrdenCompraDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarLinea(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  function agregarDistribucion(lineaIndex: number) {
    if (almacenes.length === 0) return;
    actualizarLinea(lineaIndex, {
      distribucion: [...detalle[lineaIndex].distribucion, distribucionVacia(almacenes[0].almacen_id)],
    });
  }

  function actualizarDistribucion(
    lineaIndex: number,
    distribucionIndex: number,
    patch: Partial<OrdenCompraDistribucionIn>,
  ) {
    const nuevaDistribucion = detalle[lineaIndex].distribucion.map((fila, i) =>
      i === distribucionIndex ? { ...fila, ...patch } : fila,
    );
    actualizarLinea(lineaIndex, { distribucion: nuevaDistribucion });
  }

  function quitarDistribucion(lineaIndex: number, distribucionIndex: number) {
    actualizarLinea(lineaIndex, {
      distribucion: detalle[lineaIndex].distribucion.filter((_, i) => i !== distribucionIndex),
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de detalle.");
      return;
    }

    for (const fila of detalle) {
      if (fila.distribucion.length === 0) {
        setError("Cada línea necesita al menos una distribución por almacén.");
        return;
      }
      const suma = fila.distribucion.reduce((acc, d) => acc + d.cantidad_distribuida, 0);
      if (Math.abs(suma - fila.cantidad_solicitada) > EPS) {
        setError(
          `RN-15: la distribución de una línea suma ${suma}, pero la cantidad solicitada es ${fila.cantidad_solicitada}.`,
        );
        return;
      }
    }

    const response = await crear.mutateAsync({
      data: {
        numero_oc: numeroOc,
        contrato_id: Number(contratoId),
        periodo_mes: periodoMes,
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/compras/${response.data.orden_compra_id}`);
    router.refresh();
  }

  if (contratos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un contrato VIGENTE con productos contratados
        para crear una orden de compra.
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="numero_oc" className="text-sm font-medium">
            N° de orden de compra
          </label>
          <input
            id="numero_oc"
            value={numeroOc}
            onChange={(event) => setNumeroOc(event.target.value)}
            required
            maxLength={40}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="contrato_id" className="text-sm font-medium">
            Contrato
          </label>
          <select
            id="contrato_id"
            value={contratoId}
            onChange={(event) => handleContratoChange(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {contratos.map((c) => (
              <option key={c.contrato_id} value={c.contrato_id}>
                {c.numero_contrato} — {c.proveedor_razon_social}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="periodo_mes" className="text-sm font-medium">
            Periodo (mes)
          </label>
          <input
            id="periodo_mes"
            type="date"
            value={periodoMes}
            onChange={(event) => setPeriodoMes(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            Detalle <span className="text-danger">*</span>
          </span>
          <button
            type="button"
            onClick={agregarLinea}
            disabled={productos.length === 0}
            className="text-sm text-primary hover:underline disabled:opacity-40"
          >
            + Agregar línea
          </button>
        </div>
        {productos.length === 0 && (
          <p className="text-xs text-warning">
            El contrato seleccionado no tiene productos contratados.
          </p>
        )}
        {detalle.length === 0 && productos.length > 0 && (
          <p className="text-xs text-text-secondary">Se necesita al menos una línea.</p>
        )}

        {detalle.map((fila, lineaIndex) => {
          const producto = productos.find(
            (p) => p.producto_contratado_id === fila.producto_contratado_id,
          );
          return (
            <div key={lineaIndex} className="space-y-2 rounded-md border border-border/20 p-3">
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-4 sm:items-end">
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-xs text-text-secondary">Producto contratado</label>
                  <select
                    value={fila.producto_contratado_id}
                    onChange={(event) =>
                      actualizarLinea(lineaIndex, {
                        producto_contratado_id: Number(event.target.value),
                      })
                    }
                    className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                  >
                    {productos.map((p) => (
                      <option key={p.producto_contratado_id} value={p.producto_contratado_id}>
                        {p.producto_codigo} — {p.producto_nombre} (saldo: {p.saldo_fisico})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-text-secondary">Cantidad solicitada</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={fila.cantidad_solicitada}
                    onChange={(event) =>
                      actualizarLinea(lineaIndex, {
                        cantidad_solicitada: Number(event.target.value),
                      })
                    }
                    className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => quitarLinea(lineaIndex)}
                  className="text-sm text-danger hover:underline"
                >
                  Quitar línea
                </button>
              </div>
              {producto && (
                <p className="text-xs text-text-secondary">
                  Precio de contrato: S/ {producto.precio_unitario.toFixed(2)} (RN-09, no editable)
                </p>
              )}

              <div className="space-y-1 pl-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-text-secondary">
                    Distribución por almacén (RN-15: debe sumar la cantidad solicitada)
                  </span>
                  <button
                    type="button"
                    onClick={() => agregarDistribucion(lineaIndex)}
                    disabled={almacenes.length === 0}
                    className="text-xs text-primary hover:underline disabled:opacity-40"
                  >
                    + Agregar almacén
                  </button>
                </div>
                {fila.distribucion.map((dist, distIndex) => (
                  <div key={distIndex} className="flex items-center gap-2">
                    <select
                      value={dist.almacen_id}
                      onChange={(event) =>
                        actualizarDistribucion(lineaIndex, distIndex, {
                          almacen_id: Number(event.target.value),
                        })
                      }
                      className="flex-1 rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                    >
                      {almacenes.map((almacen) => (
                        <option key={almacen.almacen_id} value={almacen.almacen_id}>
                          {almacen.codigo} — {almacen.nombre}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={dist.cantidad_distribuida}
                      onChange={(event) =>
                        actualizarDistribucion(lineaIndex, distIndex, {
                          cantidad_distribuida: Number(event.target.value),
                        })
                      }
                      className="w-32 rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => quitarDistribucion(lineaIndex, distIndex)}
                      className="text-xs text-danger hover:underline"
                    >
                      Quitar
                    </button>
                  </div>
                ))}
              </div>
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
          {crear.isPending ? "Creando..." : "Crear orden de compra"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/compras")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
