"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const ROL_LABELS: Record<string, string> = {
  ADMIN: "Administrador",
  NUTRICION: "Nutrición",
  LOGISTICA_CENTRAL: "Logística Central",
  ALMACENERO: "Almacenero",
  INSPECTOR: "Inspector de calidad",
  COCINA: "Personal de cocina",
  PAGOS: "Abastecimiento / Pagos",
  PROVEEDOR: "Proveedor",
};

export function Topbar({ rol, usuarioId }: { rol: string; usuarioId: number }) {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.push("/login");
      router.refresh();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/20 bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <div className="text-right text-sm">
          <p className="font-medium text-foreground">Usuario #{usuarioId}</p>
          <p className="text-xs text-text-secondary">
            {ROL_LABELS[rol] ?? rol}
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={loggingOut}
          className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface disabled:opacity-60"
        >
          {loggingOut ? "Saliendo..." : "Cerrar sesión"}
        </button>
      </div>
    </header>
  );
}
