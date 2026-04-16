import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  cancelPublishPlan,
  cancelRenderTask,
  checkDeviceWorkspaceHealth,
  createAccount,
  createAutomationTask,
  createDeviceWorkspace,
  createPublishPlan,
  createRenderTask,
  deleteAccount,
  deleteAsset,
  deleteAutomationTask,
  deleteDeviceWorkspace,
  deletePublishPlan,
  deleteRenderTask,
  fetchAccountGroups,
  fetchAccounts,
  fetchAsset,
  fetchAssetReferences,
  fetchAssets,
  fetchAutomationTaskRuns,
  fetchAutomationTasks,
  fetchDeviceWorkspaces,
  fetchPublishPlans,
  fetchRenderTasks,
  fetchReviewSummary,
  importAsset,
  refreshAccountStats,
  runPublishingPrecheck,
  submitPublishPlan,
  triggerAutomationTask,
  analyzeReviewProject,
  updateAutomationTask,
  updateAsset,
  updateDeviceWorkspace,
  updatePublishPlan,
  updateRenderTask,
  updateReviewSummary
} from "@/app/runtime-client";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M09-M15 Runtime client 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("使用稳定 Runtime 前缀、方法、查询参数和请求体", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });
      return okJsonResponse(sampleResponseFor(path, method));
    });

    vi.stubGlobal("fetch", fetchMock);

    await fetchAssets("video", "hook");
    await importAsset({
      filePath: "D:/tkops/assets/clip.mp4",
      type: "video",
      source: "local",
      projectId: "project-1",
      tags: '["开场"]'
    });
    await fetchAsset("asset-1");
    await updateAsset("asset-1", { name: "Clip 2", tags: '["开场", "产品"]' });
    await fetchAssetReferences("asset-1");
    const deletedAsset = await deleteAsset("asset-1");
    await fetchAccounts("group-1", "active", "creator");
    await createAccount({ name: "Creator A", platform: "tiktok", status: "active" });
    await deleteAccount("account-1");
    await fetchAccountGroups();
    await refreshAccountStats("account-1");
    await fetchDeviceWorkspaces();
    await createDeviceWorkspace({ name: "Main", root_path: "D:/tkops/workspaces/main" });
    await updateDeviceWorkspace("ws-1", { status: "healthy" });
    await deleteDeviceWorkspace("ws-1");
    await checkDeviceWorkspaceHealth("ws-1");
    await fetchAutomationTasks("enabled", "sync");
    await createAutomationTask({ name: "同步状态", type: "sync" });
    await updateAutomationTask("auto-1", { enabled: false });
    await triggerAutomationTask("auto-1");
    await fetchAutomationTaskRuns("auto-1");
    await deleteAutomationTask("auto-1");
    await fetchPublishPlans("draft");
    await createPublishPlan({ title: "发布计划", project_id: "project-1" });
    await updatePublishPlan("plan-1", { status: "ready" });
    await runPublishingPrecheck("plan-1");
    await submitPublishPlan("plan-1");
    await cancelPublishPlan("plan-1");
    await deletePublishPlan("plan-1");
    await fetchRenderTasks("queued");
    await createRenderTask({ project_id: "project-1", preset: "1080p" });
    await updateRenderTask("render-1", { progress: 20 });
    await cancelRenderTask("render-1");
    await deleteRenderTask("render-1");
    await fetchReviewSummary("project-1");
    await analyzeReviewProject("project-1");
    await updateReviewSummary("project-1", { completion_rate: 0 });

    expect(deletedAsset).toEqual({ deleted: true });

    expect(calls).toEqual([
      { path: "/api/assets?type=video&q=hook", method: "GET", body: undefined },
      {
        path: "/api/assets/import",
        method: "POST",
        body: {
          filePath: "D:/tkops/assets/clip.mp4",
          type: "video",
          source: "local",
          projectId: "project-1",
          tags: '["开场"]'
        }
      },
      { path: "/api/assets/asset-1", method: "GET", body: undefined },
      {
        path: "/api/assets/asset-1",
        method: "PATCH",
        body: { name: "Clip 2", tags: '["开场", "产品"]' }
      },
      { path: "/api/assets/asset-1/references", method: "GET", body: undefined },
      { path: "/api/assets/asset-1", method: "DELETE", body: undefined },
      {
        path: "/api/accounts?group_id=group-1&status=active&q=creator",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/accounts",
        method: "POST",
        body: { name: "Creator A", platform: "tiktok", status: "active" }
      },
      { path: "/api/accounts/account-1", method: "DELETE", body: undefined },
      { path: "/api/accounts/groups", method: "GET", body: undefined },
      { path: "/api/accounts/account-1/refresh-stats", method: "POST", body: undefined },
      { path: "/api/devices/workspaces", method: "GET", body: undefined },
      {
        path: "/api/devices/workspaces",
        method: "POST",
        body: { name: "Main", root_path: "D:/tkops/workspaces/main" }
      },
      { path: "/api/devices/workspaces/ws-1", method: "PATCH", body: { status: "healthy" } },
      { path: "/api/devices/workspaces/ws-1", method: "DELETE", body: undefined },
      { path: "/api/devices/workspaces/ws-1/health-check", method: "POST", body: undefined },
      { path: "/api/automation/tasks?status=enabled&type=sync", method: "GET", body: undefined },
      { path: "/api/automation/tasks", method: "POST", body: { name: "同步状态", type: "sync" } },
      { path: "/api/automation/tasks/auto-1", method: "PATCH", body: { enabled: false } },
      { path: "/api/automation/tasks/auto-1/trigger", method: "POST", body: undefined },
      { path: "/api/automation/tasks/auto-1/runs", method: "GET", body: undefined },
      { path: "/api/automation/tasks/auto-1", method: "DELETE", body: undefined },
      { path: "/api/publishing/plans?status=draft", method: "GET", body: undefined },
      {
        path: "/api/publishing/plans",
        method: "POST",
        body: { title: "发布计划", project_id: "project-1" }
      },
      { path: "/api/publishing/plans/plan-1", method: "PATCH", body: { status: "ready" } },
      { path: "/api/publishing/plans/plan-1/precheck", method: "POST", body: undefined },
      { path: "/api/publishing/plans/plan-1/submit", method: "POST", body: undefined },
      { path: "/api/publishing/plans/plan-1/cancel", method: "POST", body: undefined },
      { path: "/api/publishing/plans/plan-1", method: "DELETE", body: undefined },
      { path: "/api/renders/tasks?status=queued", method: "GET", body: undefined },
      {
        path: "/api/renders/tasks",
        method: "POST",
        body: { project_id: "project-1", preset: "1080p" }
      },
      { path: "/api/renders/tasks/render-1", method: "PATCH", body: { progress: 20 } },
      { path: "/api/renders/tasks/render-1/cancel", method: "POST", body: undefined },
      { path: "/api/renders/tasks/render-1", method: "DELETE", body: undefined },
      { path: "/api/review/projects/project-1/summary", method: "GET", body: undefined },
      { path: "/api/review/projects/project-1/analyze", method: "POST", body: undefined },
      {
        path: "/api/review/projects/project-1/summary",
        method: "PATCH",
        body: { completion_rate: 0 }
      }
    ]);
  });

  it("把 Runtime 错误信封转换为可见错误，不暴露 traceback", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch(() => errorJsonResponse(409, "发布前校验未通过", "req-publish"))
    );

    await expect(submitPublishPlan("plan-1")).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "发布前校验未通过",
      requestId: "req-publish",
      status: 409
    } satisfies Partial<RuntimeRequestError>);
  });
});

function sampleResponseFor(path: string, method: string): unknown {
  if (method === "DELETE" && path.startsWith("/api/assets")) return { deleted: true };
  if (method === "DELETE") return undefined;
  if (path.endsWith("/references")) return [assetReference()];
  if (path.startsWith("/api/assets")) return path.includes("?") ? [asset()] : asset();
  if (path === "/api/accounts/groups") return [accountGroup()];
  if (path.includes("/refresh-stats")) {
    return { id: "account-1", status: "active", updatedAt: now(), providerStatus: "pending_provider" };
  }
  if (path.startsWith("/api/accounts")) return path.includes("?") ? [account()] : account();
  if (path.includes("/health-check")) return { workspace_id: "ws-1", status: "healthy", checked_at: now() };
  if (path.startsWith("/api/devices/workspaces")) return path.includes("ws-1") ? workspace() : [workspace()];
  if (path.endsWith("/trigger")) return { task_id: "auto-1", run_id: "run-1", status: "running", message: "任务已触发" };
  if (path.endsWith("/runs")) return [automationRun()];
  if (path.startsWith("/api/automation/tasks")) return path.includes("?") ? [automationTask()] : automationTask();
  if (path.endsWith("/precheck")) return { plan_id: "plan-1", items: [], has_errors: false, checked_at: now() };
  if (path.endsWith("/submit")) return { plan_id: "plan-1", status: "submitted", submitted_at: now(), message: "发布计划已提交" };
  if (path.endsWith("/cancel") && path.startsWith("/api/publishing")) return publishPlan("cancelled");
  if (path.startsWith("/api/publishing/plans")) return path.includes("?") ? [publishPlan()] : publishPlan();
  if (path.endsWith("/cancel") && path.startsWith("/api/renders")) return { task_id: "render-1", status: "cancelled", message: "渲染任务已取消" };
  if (path.startsWith("/api/renders/tasks")) return path.includes("?") ? [renderTask()] : renderTask();
  if (path.endsWith("/analyze")) return { project_id: "project-1", status: "done", message: "复盘分析已完成", analyzed_at: now() };
  if (path.startsWith("/api/review")) return reviewSummary();
  return {};
}

function now() {
  return "2026-04-15T10:00:00Z";
}

function asset() {
  return { id: "asset-1", name: "Clip", type: "video", source: "local", filePath: null, fileSizeBytes: null, durationMs: null, thumbnailPath: null, tags: null, projectId: null, metadataJson: null, createdAt: now(), updatedAt: now() };
}

function assetReference() {
  return { id: "ref-1", assetId: "asset-1", referenceType: "storyboard", referenceId: "scene-1", createdAt: now() };
}

function account() {
  return { id: "account-1", name: "Creator A", platform: "tiktok", username: "creator_a", avatarUrl: null, status: "active", authExpiresAt: null, followerCount: null, followingCount: null, videoCount: null, tags: null, notes: null, createdAt: now(), updatedAt: now() };
}

function accountGroup() {
  return { id: "group-1", name: "Main", description: null, color: null, createdAt: now() };
}

function workspace() {
  return { id: "ws-1", name: "Main", root_path: "D:/tkops/workspaces/main", status: "healthy", error_count: 0, last_used_at: null, created_at: now(), updated_at: now() };
}

function automationTask() {
  return { id: "auto-1", name: "同步状态", type: "sync", enabled: true, cron_expr: null, last_run_at: null, last_run_status: null, run_count: 0, config_json: null, created_at: now(), updated_at: now() };
}

function automationRun() {
  return { id: "run-1", task_id: "auto-1", status: "running", started_at: now(), finished_at: null, log_text: null, created_at: now() };
}

function publishPlan(status = "draft") {
  return { id: "plan-1", title: "发布计划", account_id: null, account_name: null, project_id: "project-1", video_asset_id: null, status, scheduled_at: null, submitted_at: null, published_at: null, error_message: null, precheck_result_json: null, created_at: now(), updated_at: now() };
}

function renderTask() {
  return { id: "render-1", project_id: "project-1", project_name: "Demo", preset: "1080p", format: "mp4", status: "queued", progress: 0, output_path: null, error_message: null, started_at: null, finished_at: null, created_at: now(), updated_at: now() };
}

function reviewSummary() {
  return { id: "review-1", project_id: "project-1", project_name: "Demo", total_views: 0, total_likes: 0, total_comments: 0, avg_watch_time_sec: 0, completion_rate: 0, suggestions: [], last_analyzed_at: null, created_at: now(), updated_at: now() };
}
