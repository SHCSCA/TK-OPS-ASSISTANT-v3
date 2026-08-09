import { defineConfig, type UserConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    // 动态导入也需在首个页面请求前完成预构建，避免开发态热重载中断首启路由守卫。
    include: [
      "@tauri-apps/api/core",
      "@tauri-apps/api/event",
      "@tauri-apps/api/window",
      "@tauri-apps/plugin-dialog",
      "@tauri-apps/plugin-opener"
    ]
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  test: {
    environment: "jsdom",
    include: ["./tests/**/*.spec.ts"],
    testTimeout: 10000
  },
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true
  }
} as UserConfig & { test: any });
