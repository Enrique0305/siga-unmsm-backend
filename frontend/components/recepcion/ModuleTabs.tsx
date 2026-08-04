"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/recepcion", label: "Inspecciones" },
  { href: "/recepcion/actas", label: "Actas de observación" },
];

export function ModuleTabs() {
  const pathname = usePathname();

  return (
    <div className="flex gap-1 border-b border-border/20">
      {TABS.map((tab) => {
        const isActive =
          tab.href === "/recepcion"
            ? pathname === "/recepcion" ||
              pathname.startsWith("/recepcion/nuevo") ||
              /^\/recepcion\/\d+$/.test(pathname)
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
