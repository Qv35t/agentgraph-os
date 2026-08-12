import react from "@vitejs/plugin-react";
import { defineConfig as defineTestConfig } from "vitest/config";

export default defineTestConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: { environment: "jsdom", setupFiles: "./src/test/setup.ts" },
});
