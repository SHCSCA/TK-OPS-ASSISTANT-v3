/// <reference types="vitest" />
import { defineConfig, type UserConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// Use a type cast to resolve the 'test' property conflict in defineConfig
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  test: {
    environment: "jsdom",
    include: ["./tests/**/*.spec.ts"],
    testTimeout: 10000,
    globals: true
  },
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true
  }
} as UserConfig & { test: any });
