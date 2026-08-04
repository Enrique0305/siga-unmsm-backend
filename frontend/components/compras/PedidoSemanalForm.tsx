"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearPedidoSemanalApiV1PedidosSemanalesPost } from "@/lib/api/generated/endpoints/pedidos-semanales/pedidos-semanales";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { MenuQuincenalOut } from "@/lib/api/generated/model/menuQuincenalOut";
import type { OrdenCompraOut } from "@/lib/api/generated/model/ordenCompraOut";

export function PedidoSemanalForm({
  ordenesCompra,
  menus,
  almacenes,
}: {
  ordenesCompra: OrdenCompraOut[];
  menus: MenuQuincenalOut[];
  almacenes: AlmacenOut[];
}) {
  const router = useRouter();
  const crear = useCrearPedidoSemanalApiV1PedidosSemanalesPost();

  const [ordenCompraId, setOrdenCompraId] = useState<number | string>(
    ordenesCompra[0]?.orden_compra_id ?? "",
  );
  const [menuId, setMenuId] = useState<number | string>(menus[0]?.menu_id ?? "");
  const [almacenId, setAlmacenId] = useState<number | string>(
    almacenes[0]?.almacen_id ?? "",
  );
  const [semanaInicio, setSemanaInicio] = useState("");
  const [semanaFin, setSemanaFin] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        orden_compra_id: Number(ordenCompraId),
        menu_id: Number(menuId),
        almacen_id: Number(almacenId),
        semana_inicio: semanaInicio,
        semana_fin: semanaFin,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/compras/pedidos-semanales/${response.data.pedido_semanal_id}`);
    router.refresh();
  }

  if (ordenesCompra.length === 0 || menus.length === 0 || almacenes.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una orden de compra emitida, un menú
        quincenal y un almacén para crear un pedido semanal.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="orden_compra_id" className="text-sm font-medium">
          Orden de compra
        </label>
        <select
          id="orden_compra_id"
          value={ordenCompraId}
          onChange={(event) => setOrdenCompraId(event.target.value)}
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="menu_id" className="text-sm font-medium">
            Menú quincenal
          </label>
          <select
            id="menu_id"
            value={menuId}
            onChange={(event) => setMenuId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {menus.map((menu) => (
              <option key={menu.menu_id} value={menu.menu_id}>
                {menu.quincena_inicio} — {menu.quincena_fin}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="almacen_id" className="text-sm font-medium">
            Almacén
          </label>
          <select
            id="almacen_id"
            value={almacenId}
            onChange={(event) => setAlmacenId(event.target.value)}
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
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="semana_inicio" className="text-sm font-medium">
            Semana — inicio
          </label>
          <input
            id="semana_inicio"
            type="date"
            value={semanaInicio}
            onChange={(event) => setSemanaInicio(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="semana_fin" className="text-sm font-medium">
            Semana — fin
          </label>
          <input
            id="semana_fin"
            type="date"
            value={semanaFin}
            onChange={(event) => setSemanaFin(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Creando..." : "Crear pedido semanal"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/compras/pedidos-semanales")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
