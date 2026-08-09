import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createAppRouter,
  LEGACY_MIGRATION_QUERY_KEY,
  p0RouteManifest
} from "@/app/router";
import { createNavigationItems } from "@/layouts/account-workspace/account-workspace-shell-helpers";
import { useP0BootstrapStore } from "@/modules/system/bootstrap-store";

describe("P0 启动门禁与路由", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("P0 根路径默认进入账号工作台", async () => {
    const pinia = createPinia();
    const bootstrap = useP0BootstrapStore(pinia);
    bootstrap.phase = "ready";
    const router = createAppRouter(pinia, createMemoryHistory());

    await router.push("/");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/workspace");
    expect(router.currentRoute.value.meta.scope).toBe("account");
  });

  it.each([
    ["/dashboard", "/workspace"],
    ["/scripts/topics", "/scripts"],
    ["/storyboards/planning", "/storyboards"],
    ["/assets/library", "/content-library"],
    ["/publishing/center", "/publishing"]
  ])("旧路径 %s 重定向到 %s 并保留查询参数", async (legacyPath, targetPath) => {
    const pinia = createPinia();
    const bootstrap = useP0BootstrapStore(pinia);
    bootstrap.phase = "ready";
    const router = createAppRouter(pinia, createMemoryHistory());

    await router.push(`${legacyPath}?source=legacy`);
    await router.isReady();

    expect(router.currentRoute.value.path).toBe(targetPath);
    expect(router.currentRoute.value.query.source).toBe("legacy");
    expect(
      router.currentRoute.value.query[LEGACY_MIGRATION_QUERY_KEY]
    ).toBeTruthy();
  });

  it("旧剪辑入口只做薄重定向并保留查询参数与 hash", async () => {
    const pinia = createPinia();
    const bootstrap = useP0BootstrapStore(pinia);
    bootstrap.phase = "ready";
    const router = createAppRouter(pinia, createMemoryHistory());

    await router.push("/workspace/editing?clip=shot-1#preview");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/production/batches");
    expect(router.currentRoute.value.query.clip).toBe("shot-1");
    expect(
      router.currentRoute.value.query[LEGACY_MIGRATION_QUERY_KEY]
    ).toBe("editing");
    expect(router.currentRoute.value.hash).toBe("#preview");
  });

  it("未完成授权与启动检查时进入首启页并保留原目标", async () => {
    const pinia = createPinia();
    const bootstrap = useP0BootstrapStore(pinia);
    bootstrap.phase = "setup_required";
    const router = createAppRouter(pinia, createMemoryHistory());

    await router.push("/scripts?draft=local");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/setup/license");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/scripts?draft=local"
    );
  });

  it("授权就绪后从首启页返回受控的账号工作台路径", async () => {
    const pinia = createPinia();
    const bootstrap = useP0BootstrapStore(pinia);
    bootstrap.phase = "ready";
    const router = createAppRouter(pinia, createMemoryHistory());

    await router.push(
      "/setup/license?redirect=%2Fstrategy-knowledge%3Fsection%3Dprofile"
    );
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe(
      "/strategy-knowledge?section=profile"
    );
  });

  it("P0 清单固定为一个首启容器、十个账号容器与两个系统容器", () => {
    const accountScoped = p0RouteManifest.filter(
      (route) => route.scope === "account"
    );
    const systemScoped = p0RouteManifest.filter(
      (route) =>
        route.requiresLicense
        && route.scope === "system"
    );

    expect(p0RouteManifest).toHaveLength(13);
    expect(accountScoped).toHaveLength(10);
    expect(systemScoped).toHaveLength(2);
    expect(
      p0RouteManifest.find((route) => route.path === "/setup/license")
        ?.requiresLicense
    ).toBe(false);
    expect(
      p0RouteManifest.filter((route) => route.navOrder !== null)
    ).toHaveLength(11);
  });

  it("未迁移页面使用明确 P1/P2 状态，不回退旧页面", () => {
    const stateByPath = Object.fromEntries(
      p0RouteManifest.map((route) => [
        route.path,
        route.migrationState
      ])
    );

    expect(stateByPath["/scripts"]).toBe("p1_pending");
    expect(stateByPath["/production/batches"]).toBe("p1_pending");
    expect(stateByPath["/publishing"]).toBe("p2_pending");
    expect(stateByPath["/review"]).toBe("p2_pending");
  });

  it("主导航固定为十个账号入口和一个 AI 系统入口", () => {
    expect(createNavigationItems(true)).toHaveLength(10);
    expect(createNavigationItems(false)).toEqual([
      expect.objectContaining({
        id: "ai_system_settings",
        path: "/settings/ai-system"
      })
    ]);
    expect(createNavigationItems(false)).not.toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "account_management" })
      ])
    );
  });

  it("正式路由清单不再引用旧剪辑与独立媒体页面", () => {
    const componentImports = p0RouteManifest.map(
      (route) => route.componentImport
    );

    expect(componentImports).not.toEqual(
      expect.arrayContaining([
        "@/pages/workspace/AIEditingWorkspacePage.vue",
        "@/pages/voice/VoiceStudioPage.vue",
        "@/pages/subtitles/SubtitleAlignmentCenterPage.vue",
        "@/pages/renders/RenderExportCenterPage.vue"
      ])
    );
  });
});
