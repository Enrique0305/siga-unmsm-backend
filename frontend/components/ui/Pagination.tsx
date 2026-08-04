"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

export function Pagination({
  page,
  pageSize,
  total,
}: {
  page: number;
  pageSize: number;
  total: number;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const pages = pageSize > 0 ? Math.ceil(total / pageSize) : 0;

  function hrefForPage(targetPage: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(targetPage));
    return `${pathname}?${params.toString()}`;
  }

  if (pages <= 1) {
    return null;
  }

  return (
    <div className="flex items-center justify-between border-t border-border/20 px-1 py-3 text-sm text-text-secondary">
      <span>
        Página {page} de {pages} — {total} resultados
      </span>
      <div className="flex gap-2">
        <Link
          href={hrefForPage(Math.max(1, page - 1))}
          aria-disabled={page <= 1}
          className={`rounded-md border border-border/30 px-3 py-1 ${
            page <= 1
              ? "pointer-events-none opacity-40"
              : "hover:bg-surface"
          }`}
        >
          Anterior
        </Link>
        <Link
          href={hrefForPage(Math.min(pages, page + 1))}
          aria-disabled={page >= pages}
          className={`rounded-md border border-border/30 px-3 py-1 ${
            page >= pages
              ? "pointer-events-none opacity-40"
              : "hover:bg-surface"
          }`}
        >
          Siguiente
        </Link>
      </div>
    </div>
  );
}
