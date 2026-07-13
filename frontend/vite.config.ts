import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    fs: {
      // Widened so `npm run dev` can read workload/frontend/src/routes (a
      // sibling repo checkout outside this project's own root) for the
      // import.meta.glob-based route auto-discovery in routes-manifest.ts.
      allow: [path.resolve(dirname, "..")],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
  },
});
