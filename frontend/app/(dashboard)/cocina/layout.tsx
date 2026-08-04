import { ModuleTabs } from "@/components/cocina/ModuleTabs";

export default function CocinaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Cocina y consumo</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
