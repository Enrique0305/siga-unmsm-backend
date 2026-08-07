import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera .next/standalone (servidor mínimo, sin necesitar node_modules
  // completo) — usado por frontend/Dockerfile.prod para una imagen de
  // producción liviana. No afecta `next dev`.
  output: "standalone",
};

export default nextConfig;
