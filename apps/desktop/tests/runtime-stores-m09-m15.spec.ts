import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAccountManagementStore } from "@/stores/account-management";
import { useAssetLibraryStore } from "@/stores/asset-library";
import { useAutomationStore } from "@/stores/automation";
import { useDeviceWorkspacesStore } from "@/stores/device-workspaces";
import { usePublishingStore } from "@/stores/publishing";
import { useRendersStore } from "@/stores/renders";
import { useReviewStore } from "@/stores/review";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M09-M15 Pinia store Runtime 行为", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("资产与账号 store 在成功时维护列表、选择态和错误态", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/assets" && method === "GET") return okJsonResponse([asset()]);
      if (path === "/api/assets/asset-1" && method === "GET") {
        return okJsonResponse(asset("asset-1", null, "D:/tkops/assets/clip.mp4"));
      }
      if (path === "/api/assets/asset-1/references") return okJsonResponse([assetReference()]);
      if (path === "/api/assets/asset-1" && method === "DELETE") return okJsonResponse(undefined);
      if (path === "/api/accounts" && method === "GET") return okJsonResponse([account()]);
      if (path === "/api/accounts/groups") return okJsonResponse([accountGroup()]);
      if (path === "/api/accounts" && method === "POST") return okJsonResponse(account("account-2"));
      if (path === "/api/accounts/account-1/refresh-stats") {
        return okJsonResponse({
          id: "account-1",
          status: "active",
          updatedAt: now(),
          providerStatus: "pending_provider"
        });
      }
      if (path === "/api/accounts/account-1" && method === "DELETE") {
        return okJsonResponse(undefined);
      }
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const assets = useAssetLibraryStore();
    await assets.load();
    expect(assets.status).toBe("ready");
    expect(assets.viewState).toBe("ready");
    expect(assets.error).toBeNull();
    expect(assets.assets).toHaveLength(1);

    await assets.select("asset-1");
    expect(assets.selectedAsset?.filePath).toBe("D:/tkops/assets/clip.mp4");
    expect(assets.references).toHaveLength(1);

    await assets.delete("asset-1");
    expect(assets.assets).toHaveLength(0);
    expect(assets.selectedId).toBeNull();
    expect(assets.viewState).toBe("empty");

    const accounts = useAccountManagementStore();
    await accounts.load();
    expect(accounts.status).toBe("ready");
    expect(accounts.viewState).toBe("ready");
    expect(accounts.error).toBeNull();
    expect(accounts.accounts).toHaveLength(1);
    expect(accounts.groups).toHaveLength(1);

    await accounts.addAccount({ name: "Creator B", platform: "tiktok", status: "active" });
    expect(accounts.accounts.map((item) => item.id)).toContain("account-2");
    expect(accounts.showAddModal).toBe(false);

    await accounts.refreshStats("account-1");
    await accounts.removeAccount("account-1");
    expect(accounts.accounts.every((item) => item.id !== "account-1")).toBe(true);
  });

  it("设备、自动化、发布、渲染和复盘 store 执行动作后刷新或更新状态", async () => {
    const fetchMock = createRouteAwareFetch((path, method) => {
      if (path === "/api/devices/workspaces" && method === "GET") return okJsonResponse([workspace()]);
      if (path === "/api/devices/workspaces" && method === "POST") return okJsonResponse(workspace("ws-2"));
      if (path === "/api/devices/workspaces/ws-1" && method === "PATCH") return okJsonResponse(workspace("ws-1", "offline"));
      if (path === "/api/devices/workspaces/ws-1/health-check") {
        return okJsonResponse({ workspace_id: "ws-1", status: "healthy", checked_at: now() });
      }
      if (path === "/api/devices/workspaces/ws-1" && method === "DELETE") return okJsonResponse(undefined);
      if (path === "/api/automation/tasks" && method === "GET") return okJsonResponse([automationTask()]);
      if (path === "/api/automation/tasks" && method === "POST") return okJsonResponse(automationTask("auto-2"));
      if (path === "/api/automation/tasks/auto-1" && method === "PATCH") return okJsonResponse(automationTask("auto-1", false));
      if (path === "/api/automation/tasks/auto-1/trigger") {
        return okJsonResponse({ task_id: "auto-1", run_id: "run-1", status: "running", message: "任务已触发" });
      }
      if (path === "/api/automation/tasks/auto-1/runs") return okJsonResponse([automationRun()]);
      if (path === "/api/automation/tasks/auto-1" && method === "DELETE") return okJsonResponse(undefined);
      if (path === "/api/publishing/plans" && method === "GET") return okJsonResponse([publishPlan()]);
      if (path === "/api/publishing/plans" && method === "POST") return okJsonResponse(publishPlan("plan-2"));
      if (path === "/api/publishing/plans/plan-1" && method === "PATCH") return okJsonResponse(publishPlan("plan-1", "ready"));
      if (path === "/api/publishing/plans/plan-1/precheck") {
        return okJsonResponse({ plan_id: "plan-1", items: [], has_errors: false, checked_at: now() });
      }
      if (path === "/api/publishing/plans/plan-1/submit") {
        return okJsonResponse({ plan_id: "plan-1", status: "submitted", submitted_at: now(), message: "发布计划已提交" });
      }
      if (path === "/api/publishing/plans/plan-1/cancel") return okJsonResponse(publishPlan("plan-1", "cancelled"));
      if (path === "/api/publishing/plans/plan-1" && method === "DELETE") return okJsonResponse(undefined);
      if (path === "/api/renders/tasks" && method === "GET") return okJsonResponse([renderTask()]);
      if (path === "/api/renders/tasks" && method === "POST") return okJsonResponse(renderTask("render-2"));
      if (path === "/api/renders/tasks/render-1" && method === "PATCH") return okJsonResponse(renderTask("render-1", 30));
      if (path === "/api/renders/tasks/render-1/cancel") {
        return okJsonResponse({ task_id: "render-1", status: "cancelled", message: "渲染任务已取消" });
      }
      if (path === "/api/renders/tasks/render-1" && method === "DELETE") return okJsonResponse(undefined);
      if (path === "/api/review/projects/project-1/summary" && method === "GET") return okJsonResponse(reviewSummary());
      if (path === "/api/review/projects/project-1/analyze") {
        return okJsonResponse({ project_id: "project-1", status: "done", message: "复盘分析已完成", analyzed_at: now() });
      }
      if (path === "/api/review/projects/project-1/summary" && method === "PATCH") return okJsonResponse(reviewSummary("复盘项目"));
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const devices = useDeviceWorkspacesStore();
    await devices.loadWorkspaces();
    expect(devices.viewState).toBe("ready");
    await devices.addWorkspace({ name: "Backup", root_path: "D:/tkops/workspaces/backup" });
    await devices.updateWorkspace("ws-1", { status: "offline" });
    await devices.checkHealth("ws-1");
    expect(devices.workspaces[0].id).toBe("ws-1");
    expect(devices.lastHealthCheck?.status).toBe("healthy");
    expect(devices.healthCheckState).toBe("ready");

    const automation = useAutomationStore();
    await automation.loadTasks();
    expect(automation.viewState).toBe("ready");
    await automation.addTask({ name: "同步状态", type: "sync" });
    await automation.updateTask("auto-1", { enabled: false });
    await automation.triggerTask("auto-1");
    expect(automation.runsByTaskId["auto-1"]).toHaveLength(1);
    expect(automation.triggerState).toBe("ready");
    await automation.removeTask("auto-1");
    expect(automation.runsByTaskId["auto-1"]).toBeUndefined();

    const publishing = usePublishingStore();
    await publishing.loadPlans();
    expect(publishing.viewState).toBe("ready");
    await publishing.addPlan({ title: "发布计划" });
    await publishing.updatePlan("plan-1", { status: "ready" });
    await publishing.precheck("plan-1");
    expect(publishing.workflowState).toBe("ready");
    await publishing.submit("plan-1");
    await publishing.cancel("plan-1");
    await publishing.removePlan("plan-1");
    expect(publishing.precheckResult?.has_errors).toBe(false);
    expect(publishing.submitResult?.status).toBe("submitted");

    const renders = useRendersStore();
    await renders.loadTasks();
    expect(renders.viewState).toBe("ready");
    await renders.addTask({ project_id: "project-1" });
    await renders.updateTask("render-1", { progress: 30 });
    await renders.cancel("render-1");
    await renders.removeTask("render-1");
    expect(renders.lastCancelResult?.status).toBe("cancelled");

    const review = useReviewStore();
    await review.loadSummary("project-1");
    expect(review.viewState).toBe("ready");
    await review.analyze("project-1");
    await review.updateSummary("project-1", { project_name: "复盘项目" });
    expect(review.summary?.project_name).toBe("复盘项目");
    expect(review.lastAnalyzeResult?.status).toBe("done");
  });

  it("Runtime 失败时保留中文错误态并结束 loading", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch(() => errorJsonResponse(500, "设备工作区加载失败"))
    );

    const devices = useDeviceWorkspacesStore();
    await devices.loadWorkspaces();

    expect(devices.loading).toBe(false);
    expect(devices.error).toBe("设备工作区加载失败");
    expect(devices.viewState).toBe("error");
  });
  it("资产 store 支持真实导入、标签解析和删除前引用阻断", async () => {
    let references = [assetReference()];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      if (path === "/api/assets" && method === "GET") return okJsonResponse([asset()]);
      if (path === "/api/assets/import" && method === "POST") {
        expect(JSON.parse(String(init?.body))).toEqual({
          filePath: "D:/tkops/assets/opening.mp4",
          type: "video",
          source: "local",
          projectId: "project-1",
          tags: '["开场"]'
        });
        return okJsonResponse(asset("asset-2", '["开场"]'));
      }
      if (path === "/api/assets/asset-1" && method === "GET") {
        return okJsonResponse(asset("asset-1", null, "D:/tkops/assets/original.mp4"));
      }
      if (path === "/api/assets/asset-1/references") return okJsonResponse(references);
      if (path === "/api/assets/asset-1" && method === "DELETE") {
        return okJsonResponse({ deleted: true });
      }
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const assets = useAssetLibraryStore();
    await assets.load();

    const imported = await assets.importLocalFile({
      filePath: "D:/tkops/assets/opening.mp4",
      type: "video",
      source: "local",
      projectId: "project-1",
      tags: '["开场"]'
    });
    expect(imported.id).toBe("asset-2");
    expect(assets.selectedId).toBe("asset-2");
    expect(assets.importStatus).toBe("succeeded");
    expect(assets.parseTags(imported)).toEqual(["开场"]);
    expect(assets.parseTags({ ...imported, tags: "not-json" })).toEqual([]);

    const canDelete = await assets.prepareDelete("asset-1");
    expect(canDelete).toBe(false);
    expect(assets.deleteError).toContain("资产存在引用");
    expect(assets.deleteState).toBe("blocked");

    references = [];
    await assets.prepareDelete("asset-1");
    await assets.deleteSelected();
    expect(assets.assets.every((item) => item.id !== "asset-1")).toBe(true);
  });
});

function now() {
  return "2026-04-15T10:00:00Z";
}

function asset(id = "asset-1", tags: string | null = null, filePath: string | null = null) {
  return { id, name: "Clip", type: "video", source: "local", filePath, fileSizeBytes: null, durationMs: null, thumbnailPath: null, tags, projectId: null, metadataJson: null, createdAt: now(), updatedAt: now() };
}

function assetReference() {
  return { id: "ref-1", assetId: "asset-1", referenceType: "storyboard", referenceId: "scene-1", createdAt: now() };
}

function account(id = "account-1") {
  return { id, name: "Creator A", platform: "tiktok", username: "creator_a", avatarUrl: null, status: "active", authExpiresAt: null, followerCount: null, followingCount: null, videoCount: null, tags: null, notes: null, createdAt: now(), updatedAt: now() };
}

function accountGroup() {
  return { id: "group-1", name: "Main", description: null, color: null, createdAt: now() };
}

function workspace(id = "ws-1", status = "healthy") {
  return { id, name: "Main", root_path: "D:/tkops/workspaces/main", status, error_count: 0, last_used_at: null, created_at: now(), updated_at: now() };
}

function automationTask(id = "auto-1", enabled = true) {
  return { id, name: "同步状态", type: "sync", enabled, cron_expr: null, last_run_at: null, last_run_status: null, run_count: 0, config_json: null, created_at: now(), updated_at: now() };
}

function automationRun() {
  return { id: "run-1", task_id: "auto-1", status: "running", started_at: now(), finished_at: null, log_text: null, created_at: now() };
}

function publishPlan(id = "plan-1", status = "draft") {
  return { id, title: "发布计划", account_id: null, account_name: null, project_id: "project-1", video_asset_id: null, status, scheduled_at: null, submitted_at: null, published_at: null, error_message: null, precheck_result_json: null, created_at: now(), updated_at: now() };
}

function renderTask(id = "render-1", progress = 0) {
  return { id, project_id: "project-1", project_name: "Demo", preset: "1080p", format: "mp4", status: "queued", progress, output_path: null, error_message: null, started_at: null, finished_at: null, created_at: now(), updated_at: now() };
}

function reviewSummary(projectName: string | null = null) {
  return { id: "review-1", project_id: "project-1", project_name: projectName, total_views: 0, total_likes: 0, total_comments: 0, avg_watch_time_sec: 0, completion_rate: 0, suggestions: [], last_analyzed_at: null, created_at: now(), updated_at: now() };
}
