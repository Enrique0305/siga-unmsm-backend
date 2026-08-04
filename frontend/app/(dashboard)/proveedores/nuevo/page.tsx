import { ProveedorForm } from "@/components/proveedores/ProveedorForm";

export default function NuevoProveedorPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo proveedor</h2>
      <ProveedorForm mode="create" />
    </div>
  );
}
