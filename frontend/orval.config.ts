import { defineConfig } from "orval";

export default defineConfig({
  siga: {
    input: {
      target: "http://localhost:8000/api/v1/openapi.json",
    },
    output: {
      mode: "tags-split",
      target: "lib/api/generated/endpoints",
      schemas: "lib/api/generated/model",
      client: "react-query",
      httpClient: "fetch",
      mock: false,
      override: {
        mutator: {
          path: "./lib/api/mutator.ts",
          name: "apiFetch",
        },
      },
    },
  },
});
