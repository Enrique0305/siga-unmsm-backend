"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearContratoApiV1ContratosPost } from "@/lib/api/generated/endpoints/contratos/contratos";
import type { CronogramaEntregaIn } from "@/lib/api/generated/model/cronogramaEntregaIn";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";
import type { RequerimientoAnualOut } from "@/lib/api/generated/model/requerimientoAnualOut";

export function ContratoForm({
  proveedores,
  requerimientos,
}: {
  proveedores: ProveedorOut[];
  requerimientos: RequerimientoAnualOut[];
}) {
  const router = useRouter();
  const crear = useCrearContratoApiV1ContratosPost();

  const [numeroContrato, setNumeroContrato] = useState("");
  const [proveedorId, setProveedorId] = useState<number | string>(
    proveedores[0]?.proveedor_id ?? "",
  );
  const [requerimientoId, setRequerimientoId] = useState<number | string>(
    requerimientos[0]?.requerimiento_anual_id ?? "",
  );
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [presupuestoTotal, setPresupuestoTotal] = useState("");
  const [condiciones, setCondiciones] = useState("");
  const [cronograma, setCronograma] = useState<CronogramaEntregaIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarFilaCronograma() {
    setCronograma((filas) => [...filas, { periodo: "", fecha_programada: "" }]);
  }

  function actualizarFilaCronograma(index: number, patch: Partial<CronogramaEntregaIn>) {
    setCronograma((filas) =>
      filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)),
    );
  }

  function quitarFilaCronograma(index: number) {
    setCronograma((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        numero_contrato: numeroContrato,
        proveedor_id: Number(proveedorId),
        requerimiento_anual_id: Number(requerimientoId),
        fecha_inicio: fechaInicio,
        fecha_fin: fechaFin,
        presupuesto_total: Number(presupuestoTotal),
        condiciones: condiciones || null,
        cronograma: cronograma.filter((fila) => fila.periodo && fila.fecha_programada),
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/proveedores/contratos/${response.data.contrato_id}`);
    router.refresh();
  }

  if (proveedores.length === 0 || requerimientos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un proveedor activo y un requerimiento anual en
        estado APROBADO o VIGENTE para crear un contrato.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-2xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="numero_contrato" className="text-sm font-medium">
          Número de contrato
        </label>
        <input
          id="numero_contrato"
          value={numeroContrato}
          onChange={(event) => setNumeroContrato(event.target.value)}
          required
          maxLength={40}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
            {proveedores.map((proveedor) => (
              <option key={proveedor.proveedor_id} value={proveedor.proveedor_id}>
                {proveedor.razon_social} ({proveedor.ruc})
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="requerimiento_id" className="text-sm font-medium">
            Requerimiento anual
          </label>
          <select
            id="requerimiento_id"
            value={requerimientoId}
            onChange={(event) => setRequerimientoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {requerimientos.map((requerimiento) => (
              <option
                key={requerimiento.requerimiento_anual_id}
                value={requerimiento.requerimiento_anual_id}
              >
                Requerimiento #{requerimiento.requerimiento_anual_id} — v
                {requerimiento.version} ({requerimiento.estado})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="fecha_inicio" className="text-sm font-medium">
            Fecha inicio
          </label>
          <input
            id="fecha_inicio"
            type="date"
            value={fechaInicio}
            onChange={(event) => setFechaInicio(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="fecha_fin" className="text-sm font-medium">
            Fecha fin
          </label>
          <input
            id="fecha_fin"
            type="date"
            value={fechaFin}
            onChange={(event) => setFechaFin(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="presupuesto_total" className="text-sm font-medium">
            Presupuesto total (S/)
          </label>
          <input
            id="presupuesto_total"
            type="number"
            min="0.01"
            step="0.01"
            value={presupuestoTotal}
            onChange={(event) => setPresupuestoTotal(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="condiciones" className="text-sm font-medium">
          Condiciones (opcional)
        </label>
        <textarea
          id="condiciones"
          value={condiciones}
          onChange={(event) => setCondiciones(event.target.value)}
          rows={3}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Cronograma de entrega</span>
          <button
            type="button"
            onClick={agregarFilaCronograma}
            className="text-sm text-primary hover:underline"
          >
            + Agregar fila
          </button>
        </div>
        {cronograma.length === 0 && (
          <p className="text-xs text-text-secondary">
            Sin filas de cronograma (opcional, se puede dejar vacío).
          </p>
        )}
        {cronograma.map((fila, index) => (
          <div key={index} className="flex items-center gap-2">
            <input
              placeholder="Periodo (ej. Semana 1)"
              value={fila.periodo}
              onChange={(event) =>
                actualizarFilaCronograma(index, { periodo: event.target.value })
              }
              maxLength={20}
              className="flex-1 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
            />
            <input
              type="date"
              value={fila.fecha_programada}
              onChange={(event) =>
                actualizarFilaCronograma(index, { fecha_programada: event.target.value })
              }
              className="rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
            />
            <button
              type="button"
              onClick={() => quitarFilaCronograma(index)}
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
          {crear.isPending ? "Creando..." : "Crear contrato"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/proveedores/contratos")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
