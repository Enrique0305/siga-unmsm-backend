"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { ProductoOut } from "@/lib/api/generated/model/productoOut";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";

export function ComparativoConsumoForm({
  productos,
  proveedores,
}: {
  productos: ProductoOut[];
  proveedores: ProveedorOut[];
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [productoId, setProductoId] = useState(
    searchParams.get("producto_id") ?? String(productos[0]?.producto_id ?? ""),
  );
  const [fechaInicio, setFechaInicio] = useState(searchParams.get("fecha_inicio") ?? "");
  const [fechaFin, setFechaFin] = useState(searchParams.get("fecha_fin") ?? "");
  const [proveedorId, setProveedorId] = useState(searchParams.get("proveedor_id") ?? "");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    params.set("producto_id", productoId);
    params.set("fecha_inicio", fechaInicio);
    params.set("fecha_fin", fechaFin);
    if (proveedorId) params.set("proveedor_id", proveedorId);
    router.push(`/reportes/comparativo?${params.toString()}`);
  }

  if (productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        No hay productos registrados para consultar.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <label htmlFor="producto_id" className="text-sm font-medium">
          Producto
        </label>
        <select
          id="producto_id"
          value={productoId}
          onChange={(event) => setProductoId(event.target.value)}
          required
          className="w-64 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {productos.map((producto) => (
            <option key={producto.producto_id} value={producto.producto_id}>
              {producto.codigo} — {producto.nombre}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <label htmlFor="fecha_inicio" className="text-sm font-medium">
          Desde
        </label>
        <input
          id="fecha_inicio"
          type="date"
          value={fechaInicio}
          onChange={(event) => setFechaInicio(event.target.value)}
          required
          className="rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="fecha_fin" className="text-sm font-medium">
          Hasta
        </label>
        <input
          id="fecha_fin"
          type="date"
          value={fechaFin}
          onChange={(event) => setFechaFin(event.target.value)}
          required
          className="rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
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
          className="w-64 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="">Todos (solo filtra &quot;Comprado&quot;)</option>
          {proveedores.map((proveedor) => (
            <option key={proveedor.proveedor_id} value={proveedor.proveedor_id}>
              {proveedor.razon_social}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
      >
        Consultar
      </button>
    </form>
  );
}
