"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/reportes", label: "Valorización" },
  { href: "/reportes/comparativo", label: "Comparativo de consumo" },
  { href: "/reportes/alertas", label: "Alertas" },
  { href: "/reportes/auditoria", label: "Auditoría" },
  { href: "/reportes/notificaciones", label: "Notificaciones" },
];

export function ModuleTabs() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-1 border-b border-border/20">
      {TABS.map((tab) => {
        const isActive =
          tab.href === "/reportes" ? pathname === "/reportes" : pathname.startsWith(tab.href);

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
