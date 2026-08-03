"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/lib/nav";

export function Sidebar({ rol }: { rol: string }) {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((item) => item.roles.includes(rol));

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border/20 bg-white">
      <div className="px-5 py-5">
        <p className="text-lg font-semibold text-primary">SIGA-UNMSM</p>
        <p className="text-xs text-text-secondary">Almacén y Abastecimiento</p>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {items.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-primary text-white"
                  : "text-foreground hover:bg-surface"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
