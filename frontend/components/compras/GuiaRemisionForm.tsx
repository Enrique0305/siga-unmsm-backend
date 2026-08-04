"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearGuiaRemisionApiV1GuiasRemisionPost } from "@/lib/api/generated/endpoints/guías-de-remisión/guías-de-remisión";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { GuiaRemisionDetalleIn } from "@/lib/api/generated/model/guiaRemisionDetalleIn";
import type { OrdenCompraDetailOut } from "@/lib/api/generated/model/ordenCompraDetailOut";
import type { PedidoSemanalOut } from "@/lib/api/generated/model/pedidoSemanalOut";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";

function filaVacia(ordenCompraDetalleId: number): GuiaRemisionDetalleIn {
  return {
    orden_compra_detalle_id: ordenCompraDetalleId,
    cantidad_entregada: 0,
    lote: null,
    fecha_vencimiento: null,
  };
}

export function GuiaRemisionForm({
  proveedores,
  ordenesCompra,
  pedidosSemanales,
  almacenes,
}: {
  proveedores: ProveedorOut[];
  ordenesCompra: OrdenCompraDetailOut[];
  pedidosSemanales: PedidoSemanalOut[];
  almacenes: AlmacenOut[];
}) {
  const router = useRouter();
  const crear = useCrearGuiaRemisionApiV1GuiasRemisionPost();

  const [numeroGuia, setNumeroGuia] = useState("");
  const [proveedorId, setProveedorId] = useState<number | string>(
    proveedores[0]?.proveedor_id ?? "",
  );
  const [ordenCompraId, setOrdenCompraId] = useState<number | string>(
    ordenesCompra[0]?.orden_compra_id ?? "",
  );
  const [pedidoSemanalId, setPedidoSemanalId] = useState<number | string>(
    () =>
      pedidosSemanales.find((p) => p.orden_compra_id === ordenesCompra[0]?.orden_compra_id)
        ?.pedido_semanal_id ?? "",
  );
  const [almacenDestinoId, setAlmacenDestinoId] = useState<number | string>(
    almacenes[0]?.almacen_id ?? "",
  );
  const [fechaEntrega, setFechaEntrega] = useState("");
  const [detalle, setDetalle] = useState<GuiaRemisionDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  const ordenCompra = useMemo(
    () => ordenesCompra.find((oc) => oc.orden_compra_id === Number(ordenCompraId)),
    [ordenesCompra, ordenCompraId],
  );
  const lineasOc = ordenCompra?.detalle ?? [];
  const pedidosDeLaOc = useMemo(
    () => pedidosSemanales.filter((p) => p.orden_compra_id === Number(ordenCompraId)),
    [pedidosSemanales, ordenCompraId],
  );

  function handleOrdenCompraChange(value: string) {
    setOrdenCompraId(value);
    setDetalle([]);
    const opciones = pedidosSemanales.filter((p) => p.orden_compra_id === Number(value));
    setPedidoSemanalId(opciones[0]?.pedido_semanal_id ?? "");
  }

  function agregarLinea() {
    if (lineasOc.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(lineasOc[0].orden_compra_detalle_id)]);
  }

  function actualizarLinea(index: number, patch: Partial<GuiaRemisionDetalleIn>) {
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
    if (!pedidoSemanalId) {
      setError("Se necesita un pedido semanal para esta orden de compra.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        numero_guia: numeroGuia,
        proveedor_id: Number(proveedorId),
        orden_compra_id: Number(ordenCompraId),
        pedido_semanal_id: Number(pedidoSemanalId),
        almacen_destino_id: Number(almacenDestinoId),
        fecha_entrega: fechaEntrega,
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/compras/guias/${response.data.guia_remision_id}`);
    router.refresh();
  }

  if (proveedores.length === 0 || ordenesCompra.length === 0 || almacenes.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un proveedor, una orden de compra emitida y
        un almacén para crear una guía de remisión.
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
          <label htmlFor="numero_guia" className="text-sm font-medium">
            N° de guía
          </label>
          <input
            id="numero_guia"
            value={numeroGuia}
            onChange={(event) => setNumeroGuia(event.target.value)}
            required
            maxLength={40}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="proveedor_id" className="text-sm font-medium">
            Proveedor
          </label>
          <select
            id="proveedor_id"
            value={proveedorId}
            onChange={(event) => setProveedorId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {proveedores.map((p) => (
              <option key={p.proveedor_id} value={p.proveedor_id}>
                {p.razon_social}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="orden_compra_id" className="text-sm font-medium">
            Orden de compra
          </label>
          <select
            id="orden_compra_id"
            value={ordenCompraId}
            onChange={(event) => handleOrdenCompraChange(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {ordenesCompra.map((oc) => (
              <option key={oc.orden_compra_id} value={oc.orden_compra_id}>
                {oc.numero_oc}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="pedido_semanal_id" className="text-sm font-medium">
            Pedido semanal (RN-02: debe ser de esta OC)
          </label>
          <select
            id="pedido_semanal_id"
            value={pedidoSemanalId}
            onChange={(event) => setPedidoSemanalId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {pedidosDeLaOc.length === 0 && (
              <option value="">Sin pedidos semanales para esta OC</option>
            )}
            {pedidosDeLaOc.map((p) => (
              <option key={p.pedido_semanal_id} value={p.pedido_semanal_id}>
                {p.semana_inicio} — {p.semana_fin}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="almacen_destino_id" className="text-sm font-medium">
            Almacén destino (RN-13)
          </label>
          <select
            id="almacen_destino_id"
            value={almacenDestinoId}
            onChange={(event) => setAlmacenDestinoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {almacenes.map((almacen) => (
              <option key={almacen.almacen_id} value={almacen.almacen_id}>
                {almacen.codigo} — {almacen.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="fecha_entrega" className="text-sm font-medium">
            Fecha de entrega
          </label>
          <input
            id="fecha_entrega"
            type="date"
            value={fechaEntrega}
            onChange={(event) => setFechaEntrega(event.target.value)}
            required
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
            onClick={agregarLinea}
            disabled={lineasOc.length === 0}
            className="text-sm text-primary hover:underline disabled:opacity-40"
          >
            + Agregar línea
          </button>
        </div>
        {lineasOc.length === 0 && (
          <p className="text-xs text-warning">
            La orden de compra seleccionada no tiene líneas de detalle.
          </p>
        )}
        {detalle.length === 0 && lineasOc.length > 0 && (
          <p className="text-xs text-text-secondary">Se necesita al menos una línea.</p>
        )}
        {detalle.map((fila, index) => {
          const linea = lineasOc.find(
            (l) => l.orden_compra_detalle_id === fila.orden_compra_detalle_id,
          );
          return (
            <div
              key={index}
              className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-6 sm:items-end"
            >
              <div className="space-y-1 sm:col-span-2">
                <label className="text-xs text-text-secondary">Línea de OC</label>
                <select
                  value={fila.orden_compra_detalle_id}
                  onChange={(event) =>
                    actualizarLinea(index, {
                      orden_compra_detalle_id: Number(event.target.value),
                    })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                >
                  {lineasOc.map((l) => (
                    <option key={l.orden_compra_detalle_id} value={l.orden_compra_detalle_id}>
                      {l.producto_codigo} — {l.producto_nombre} (saldo: {l.saldo_oc}
                      {l.total_excedente_autorizado > 0
                        ? ` + ${l.total_excedente_autorizado} exced.`
                        : ""}
                      )
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Cant. entregada</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={fila.cantidad_entregada}
                  onChange={(event) =>
                    actualizarLinea(index, { cantidad_entregada: Number(event.target.value) })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Lote (opcional)</label>
                <input
                  value={fila.lote ?? ""}
                  onChange={(event) =>
                    actualizarLinea(index, { lote: event.target.value || null })
                  }
                  maxLength={60}
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-text-secondary">Vencimiento (opcional)</label>
                <input
                  type="date"
                  value={fila.fecha_vencimiento ?? ""}
                  onChange={(event) =>
                    actualizarLinea(index, { fecha_vencimiento: event.target.value || null })
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
              {linea && (
                <p className="col-span-full text-xs text-text-secondary">
                  RN-03: el saldo disponible es {linea.saldo_oc} + {linea.total_excedente_autorizado}{" "}
                  de excedente autorizado.
                </p>
              )}
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
          {crear.isPending ? "Creando..." : "Crear guía de remisión"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/compras/guias")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
