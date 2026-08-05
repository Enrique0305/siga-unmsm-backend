"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/almacenes", label: "Almacenes" },
  { href: "/almacenes/ubicaciones", label: "Ubicaciones" },
  { href: "/almacenes/ingresos", label: "Ingresos" },
  { href: "/almacenes/stock", label: "Stock" },
  { href: "/almacenes/kardex", label: "Kardex" },
  { href: "/almacenes/movimientos", label: "Movimientos" },
  { href: "/almacenes/inventarios", label: "Inventarios físicos" },
  { href: "/almacenes/transferencias", label: "Transferencias" },
  { href: "/almacenes/parametros", label: "Parámetros de stock" },
];

export function ModuleTabs() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-1 border-b border-border/20">
      {TABS.map((tab) => {
        const isActive =
          tab.href === "/almacenes"
            ? pathname === "/almacenes" ||
              pathname.startsWith("/almacenes/nuevo") ||
              /^\/almacenes\/\d+\/editar$/.test(pathname)
            : pathname.startsWith(tab.href);

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`border-b-2 px-4 py-2 text-sm font-medium ${
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-text-secondary hover:text-foreground"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
