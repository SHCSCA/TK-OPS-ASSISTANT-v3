import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  test: {
    environment: "jsdom",
    include: ["../../tests/desktop/**/*.spec.ts"]
  },
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true
  }
});
