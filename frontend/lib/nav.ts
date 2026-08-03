export type NavItem = {
  href: string;
  label: string;
  roles: string[];
};

/**
 * Mapa del sitio (docs/01_diseno_sistema_SIGA-UNMSM.md, sección 3) filtrado
 * por rol según la tabla de la sección 2. Roles exactos: ver CLAUDE.md
 * sección 4 — deben coincidir con `require_roles(...)` del backend.
 */
export const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Dashboard ejecutivo",
    roles: [
      "ADMIN",
      "NUTRICION",
      "LOGISTICA_CENTRAL",
      "ALMACENERO",
      "INSPECTOR",
      "COCINA",
      "PAGOS",
      "PROVEEDOR",
    ],
  },
  {
    href: "/planificacion",
    label: "Planificación anual",
    roles: ["ADMIN", "NUTRICION"],
  },
  {
    href: "/dosificacion",
    label: "Dosificación nutricional",
    roles: ["ADMIN", "NUTRICION"],
  },
  {
    href: "/proveedores",
    label: "Proveedores y contratos",
    roles: ["ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR"],
  },
  {
    href: "/compras",
    label: "Compras",
    roles: ["ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR"],
  },
  {
    href: "/recepcion",
    label: "Recepción y calidad",
    roles: ["ADMIN", "LOGISTICA_CENTRAL", "INSPECTOR", "ALMACENERO"],
  },
  {
    href: "/almacenes",
    label: "Almacenes",
    roles: ["ADMIN", "LOGISTICA_CENTRAL", "ALMACENERO"],
  },
  {
    href: "/cocina",
    label: "Cocina y consumo",
    roles: ["ADMIN", "ALMACENERO", "COCINA"],
  },
  {
    href: "/conformidad",
    label: "Conformidad y pagos",
    roles: ["ADMIN", "LOGISTICA_CENTRAL", "PAGOS"],
  },
  {
    href: "/reportes",
    label: "Reportes y auditoría",
    roles: ["ADMIN", "LOGISTICA_CENTRAL"],
  },
  {
    href: "/administracion",
    label: "Administración",
    roles: ["ADMIN"],
  },
];
