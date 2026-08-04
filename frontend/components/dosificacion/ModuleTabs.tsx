"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dosificacion", label: "Alimentos" },
  { href: "/dosificacion/recetas", label: "Recetas" },
  { href: "/dosificacion/calcular", label: "Calcular dosificación" },
];

export function ModuleTabs() {
  const pathname = usePathname();

  return (
    <div className="flex gap-1 border-b border-border/20">
      {TABS.map((tab) => {
        const isActive =
          tab.href === "/dosificacion"
            ? pathname === "/dosificacion" ||
              pathname.startsWith("/dosificacion/nuevo") ||
              /^\/dosificacion\/\d+$/.test(pathname)
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
