"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export function SearchBar({ placeholder = "Buscar..." }: { placeholder?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(searchParams.get("buscar") ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    return () => clearTimeout(debounceRef.current);
  }, []);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const next = event.target.value;
    setValue(next);

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (next) {
        params.set("buscar", next);
      } else {
        params.delete("buscar");
      }
      params.set("page", "1");
      router.push(`${pathname}?${params.toString()}`);
    }, 400);
  }

  return (
    <input
      type="search"
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      className="w-full max-w-xs rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none sm:w-64"
    />
  );
}
