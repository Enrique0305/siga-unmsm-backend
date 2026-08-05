"use client";

import { useRouter } from "next/navigation";

import { useMarcarNotificacionLeidaApiV1NotificacionesNotificacionIdLeidaPatch } from "@/lib/api/generated/endpoints/notificaciones/notificaciones";

export function MarcarLeidaButton({ notificacionId }: { notificacionId: number }) {
  const router = useRouter();
  const marcarLeida = useMarcarNotificacionLeidaApiV1NotificacionesNotificacionIdLeidaPatch();

  async function handleClick() {
    await marcarLeida.mutateAsync({ notificacionId });
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={marcarLeida.isPending}
      className="text-sm font-medium text-primary hover:underline disabled:opacity-60"
    >
      {marcarLeida.isPending ? "Marcando..." : "Marcar leída"}
    </button>
  );
}
