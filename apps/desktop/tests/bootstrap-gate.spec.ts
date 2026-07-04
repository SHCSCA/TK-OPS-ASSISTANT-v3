import { flushPromises } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createRouteAwareFetch,
  mountApp,
  okJsonResponse,
  runtimeFixtures
} from "./runtime-helpers";

describe("Bootstrap gate", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a standalone license bootstrap screen before the workspace shell", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path) => {
        if (path === "/api/license/status") {
          return okJsonResponse(runtimeFixtures.restrictedLicense);
        }
        if (path === "/api/settings/health") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config") {
          return okJsonResponse(runtimeFixtures.config);
        }
        if (path === "/api/settings/diagnostics") {
          return okJsonResponse(runtimeFixtures.diagnostics);
        }
        if (path === "/api/bootstrap/readiness") {
          return okJsonResponse(runtimeFixtures.blockedBootstrapReadiness);
        }

        throw new Error(`Unhandled request: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="license"]').exists()).toBe(true);
    expect(wrapper.find('[data-field="activationCode"]').exists()).toBe(true);
    expect(wrapper.find(".title-bar").exists()).toBe(false);
    expect(wrapper.find(".sidebar").exists()).toBe(false);
    expect(wrapper.text()).toContain("当前需要完成永久授权");
  });

  it("shows a styled diagnostic screen when Runtime bootstrap fails", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path) => {
        if (path === "/api/license/status") {
          return okJsonResponse(runtimeFixtures.activeLicense);
        }
        throw new Error(`Runtime offline: ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="error"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="bootstrap-error-panel"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="bootstrap-error-checklist"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("启动检查未完成");
    expect(wrapper.text()).toContain("Runtime 配置请求失败");
    expect(wrapper.text()).toContain("确认本地 Runtime 服务已启动");
    expect(wrapper.find(".title-bar").exists()).toBe(false);
    expect(wrapper.find(".sidebar").exists()).toBe(false);
  });

  it("keeps the shell blocked when Runtime readiness reports blockers", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/license/status" && method === "GET") {
          return okJsonResponse(runtimeFixtures.activeLicense);
        }
        if (path === "/api/settings/health" && method === "GET") {
          return okJsonResponse(runtimeFixtures.health);
        }
        if (path === "/api/settings/config" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedConfig);
        }
        if (path === "/api/settings/diagnostics" && method === "GET") {
          return okJsonResponse(runtimeFixtures.initializedDiagnostics);
        }
        if (path === "/api/bootstrap/readiness" && method === "GET") {
          return okJsonResponse({
            ...runtimeFixtures.blockedBootstrapReadiness,
            items: [
              {
                ...runtimeFixtures.blockedBootstrapReadiness.items[0],
                key: "directories",
                label: "目录初始化",
                detail: "导出目录不可写。",
                affectedTarget: "导出目录",
                blockedReason: "导出目录当前不可写。",
                nextStep: "请释放目录占用或切换到可写目录。"
              }
            ],
            blockers: [
              {
                ...runtimeFixtures.blockedBootstrapReadiness.blockers[0],
                key: "directories",
                affectedTarget: "导出目录",
                blockedReason: "导出目录当前不可写。",
                nextStep: "请释放目录占用或切换到可写目录。"
              }
            ]
          });
        }

        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const { wrapper } = await mountApp("/dashboard");
    await flushPromises();

    expect(wrapper.find('[data-bootstrap-screen="initialization"]').exists()).toBe(true);
    expect(wrapper.find(".title-bar").exists()).toBe(false);
    expect(wrapper.find(".sidebar").exists()).toBe(false);
    expect(wrapper.text()).toContain("导出目录当前不可写");
    expect(wrapper.text()).toContain("请释放目录占用或切换到可写目录");
  });

  it("imports the shared bootstrap screen stylesheet", () => {
    const indexCss = readFileSync(join(process.cwd(), "src/styles/index.css"), "utf8");
    const bootstrapCss = readFileSync(join(process.cwd(), "src/styles/bootstrap.css"), "utf8");

    expect(indexCss).toContain('@import "./bootstrap.css";');
    expect(bootstrapCss).toContain(".bootstrap-screen {");
    expect(bootstrapCss).toContain(".bootstrap-screen__panel {");
    expect(bootstrapCss).toContain(".bootstrap-error__checklist {");
  });

  it("keeps bootstrap panels centered and uses slower boot animations", () => {
    const bootstrapCss = readFileSync(join(process.cwd(), "src/styles/bootstrap.css"), "utf8");
    const errorScreen = readFileSync(
      join(process.cwd(), "src/bootstrap/BootstrapErrorScreen.vue"),
      "utf8"
    );
    const loadingScreen = readFileSync(
      join(process.cwd(), "src/bootstrap/BootstrapLoadingScreen.vue"),
      "utf8"
    );

    expect(bootstrapCss).toContain("place-items: center;");
    expect(bootstrapCss).toContain("--bootstrap-panel-enter-duration: 720ms;");
    expect(bootstrapCss).not.toContain("--bootstrap-error-breathe-duration");
    expect(bootstrapCss).not.toContain("--bootstrap-dot-pulse-duration");
    expect(bootstrapCss).toContain("animation: pulse-dot var(--motion-pulse) ease-in-out infinite;");
    expect(errorScreen).toContain("var(--bootstrap-panel-enter-duration)");
    expect(errorScreen).toContain("animation: exception-breathe var(--motion-breathe) ease-in-out infinite;");
    expect(loadingScreen).toContain("var(--bootstrap-panel-enter-duration)");
  });
});
