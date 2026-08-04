"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function SelectFilter({
  paramName,
  label,
  options,
}: {
  paramName: string;
  label: string;
  options: { value: string; label: string }[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const current = searchParams.get(paramName) ?? "";

  function handleChange(event: React.ChangeEvent<HTMLSelectElement>) {
    const params = new URLSearchParams(searchParams.toString());
    if (event.target.value) {
      params.set(paramName, event.target.value);
    } else {
      params.delete(paramName);
    }
    params.set("page", "1");
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <label className="flex items-center gap-2 text-sm text-text-secondary">
      {label}
      <select
        value={current}
        onChange={handleChange}
        className="rounded-md border border-border/30 px-2 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
