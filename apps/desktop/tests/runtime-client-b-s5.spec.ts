import { afterEach, describe, expect, it, vi } from "vitest";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("B-S5 Runtime client contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses canonical B-S5 routes and request shapes", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });
        return okJsonResponse(sampleResponse(path, method));
      })
    );

    const runtimeClient = await import("@/app/runtime-client");

    await runtimeClient.listAssetGroups();
    await runtimeClient.createAssetGroup({ name: "主分组", parentId: null });
    await runtimeClient.updateAssetGroup("group-1", { name: "主分组 v2" });
    await runtimeClient.deleteAssetGroup("group-1");
    await runtimeClient.batchDeleteAssets(["asset-1", "asset-2"]);
    await runtimeClient.batchMoveAssetsToGroup(["asset-1"], "group-1");
    await runtimeClient.setAccountBinding("account-1", {
      browserInstanceId: "browser-1",
      status: "active"
    });
    await runtimeClient.fetchExecutionBindings();
    await runtimeClient.fetchWorkspaceLogs("workspace-1", "2026-04-17T00:00:00Z");
    await runtimeClient.fetchBrowserInstances("workspace-1");
    await runtimeClient.createBrowserInstance("workspace-1", {
      name: "默认浏览器",
      profilePath: "D:/tkops/workspaces/main/profiles/default"
    });
    await runtimeClient.startBrowserInstance("workspace-1", "browser-1");
    await runtimeClient.checkBrowserInstanceHealth("workspace-1", "browser-1");
    await runtimeClient.stopBrowserInstance("workspace-1", "browser-1");
    await runtimeClient.pauseAutomationTask("auto-1");
    await runtimeClient.resumeAutomationTask("auto-1");
    await runtimeClient.fetchPublishingCalendar();
    await runtimeClient.fetchPublishReceipt("plan-1");
    await runtimeClient.fetchPublishReceipts("plan-1");
    await runtimeClient.fetchExportProfiles();
    await runtimeClient.createExportProfile({
      name: "TikTok 竖屏",
      resolution: "1080x1920"
    });
    await runtimeClient.listRenderTemplates();
    await runtimeClient.fetchRenderResourceUsage();
    await runtimeClient.retryRenderTask("render-1");
    await runtimeClient.adoptReviewSuggestion("project-1", "suggestion-1");

    expect(calls).toEqual([
      { path: "/api/assets/groups", method: "GET", body: undefined },
      {
        path: "/api/assets/groups",
        method: "POST",
        body: { name: "主分组", parentId: null }
      },
      {
        path: "/api/assets/groups/group-1",
        method: "PATCH",
        body: { name: "主分组 v2" }
      },
      { path: "/api/assets/groups/group-1", method: "DELETE", body: undefined },
      {
        path: "/api/assets/batch-delete",
        method: "POST",
        body: { assetIds: ["asset-1", "asset-2"] }
      },
      {
        path: "/api/assets/batch-move-group",
        method: "POST",
        body: { assetIds: ["asset-1"], groupId: "group-1" }
      },
      {
        path: "/api/accounts/account-1/binding",
        method: "PUT",
        body: {
          browserInstanceId: "browser-1",
          status: "active"
        }
      },
      {
        path: "/api/devices/bindings",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/devices/workspaces/workspace-1/logs?since=2026-04-17T00%3A00%3A00Z",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/devices/workspaces/workspace-1/browser-instances",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/devices/workspaces/workspace-1/browser-instances",
        method: "POST",
        body: {
          name: "默认浏览器",
          profilePath: "D:/tkops/workspaces/main/profiles/default"
        }
      },
      {
        path: "/api/devices/workspaces/workspace-1/browser-instances/browser-1/start",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/devices/workspaces/workspace-1/browser-instances/browser-1/health-check",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/devices/workspaces/workspace-1/browser-instances/browser-1/stop",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/automation/tasks/auto-1/pause",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/automation/tasks/auto-1/resume",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/publishing/calendar",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/publishing/plans/plan-1/receipt",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/publishing/plans/plan-1/receipts",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/renders/profiles",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/renders/profiles",
        method: "POST",
        body: {
          name: "TikTok 竖屏",
          resolution: "1080x1920"
        }
      },
      {
        path: "/api/renders/templates",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/renders/resource-usage",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/renders/tasks/render-1/retry",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/review/projects/project-1/suggestions/suggestion-1/adopt",
        method: "POST",
        body: undefined
      }
    ]);
  });
});

function sampleResponse(path: string, method: string): unknown {
  if (path === "/api/assets/groups" && method === "GET") {
    return [assetGroup()];
  }
  if (path.startsWith("/api/assets/groups") && method === "DELETE") {
    return undefined;
  }
  if (path.startsWith("/api/assets/groups")) {
    return assetGroup();
  }
  if (path.endsWith("/batch-delete")) {
    return { deletedIds: ["asset-1", "asset-2"] };
  }
  if (path.endsWith("/batch-move-group")) {
    return { movedIds: ["asset-1"], groupId: "group-1" };
  }
  if (path === "/api/devices/bindings") {
    return [
      {
        id: "binding-1",
        accountId: "account-1",
        browserInstanceId: "browser-1",
        status: "active",
        source: null,
        maskedMetadataJson: null,
        createdAt: "2026-04-17T12:00:00Z",
        updatedAt: "2026-04-17T12:00:00Z"
      }
    ];
  }
  if (path.includes("/binding")) {
    return {
      id: "binding-1",
      accountId: "account-1",
      browserInstanceId: "browser-1",
      status: "active",
      source: null,
      maskedMetadataJson: null,
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:00:00Z"
    };
  }
  if (path.includes("/logs")) {
    return [
      {
        id: "log-1",
        workspaceId: "workspace-1",
        kind: "health-check",
        level: "info",
        message: "workspace.ready",
        contextJson: null,
        createdAt: "2026-04-17T12:00:00Z"
      }
    ];
  }
  if (path.includes("/browser-instances/browser-1")) {
    return {
      saved: true,
      updatedAt: "2026-04-17T12:00:00Z",
      versionOrRevision: "1",
      objectSummary: { id: "browser-1", name: "默认浏览器" },
      browserInstance: browserInstance(path.includes("/start") ? "running" : path.includes("/stop") ? "stopped" : "ready")
    };
  }
  if (path.includes("/browser-instances")) {
    return method === "GET" ? [browserInstance()] : browserInstance();
  }
  if (path.endsWith("/pause") || path.endsWith("/resume")) {
    return {
      id: "auto-1",
      name: "自动化任务",
      type: "sync",
      enabled: path.endsWith("/resume"),
      cron_expr: null,
      last_run_at: null,
      last_run_status: null,
      run_count: 0,
      config_json: null,
      created_at: "2026-04-17T12:00:00Z",
      updated_at: "2026-04-17T12:00:00Z"
    };
  }
  if (path.startsWith("/api/publishing/calendar")) {
    return {
      items: [
        {
          plan_id: "plan-1",
          title: "发布计划",
          status: "ready",
          scheduled_at: "2026-04-17T12:00:00Z",
          account_name: "Creator A",
          conflict_count: 0
        }
      ],
      generated_at: "2026-04-17T12:00:00Z"
    };
  }
  if (path.endsWith("/receipts")) {
    return [
      {
        id: "receipt-1",
        plan_id: "plan-1",
        status: "manual_required",
        external_url: null,
        error_message: null,
        completed_at: null,
        created_at: "2026-04-17T12:00:00Z"
      }
    ];
  }
  if (path.endsWith("/receipt")) {
    return publishReceipt();
  }
  if (path === "/api/renders/profiles" || path === "/api/renders/templates") {
    return method === "GET" ? [exportProfile()] : exportProfile();
  }
  if (path === "/api/renders/resource-usage") {
    return {
      cpu: { status: "ready", usagePct: 10, message: null },
      gpu: { status: "unavailable", usagePct: null, message: "未检测到 GPU" },
      disk: { status: "ready", path: "D:/tkops", totalBytes: 1000, usedBytes: 100, freeBytes: 900, usagePct: 10, message: null },
      collectedAt: "2026-04-17T12:00:00Z"
    };
  }
  if (path.endsWith("/retry")) {
    return renderTask();
  }
  if (path.includes("/adopt")) {
    return {
      id: "project-child-1",
      name: "复盘子项目",
      description: "由建议回流生成",
      status: "draft",
      currentScriptVersion: 1,
      currentStoryboardVersion: 1,
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:00:00Z",
      lastAccessedAt: "2026-04-17T12:00:00Z"
    };
  }
  return {};
}

function publishReceipt() {
  return {
    id: "receipt-1",
    plan_id: "plan-1",
    status: "receipt_pending",
    stage: "receipt",
    summary: "已提交平台，等待平台回执。",
    error_code: null,
    error_message: null,
    next_action: null,
    is_final: false,
    platform_response_json: null,
    received_at: "2026-04-17T12:00:00Z",
    created_at: "2026-04-17T12:00:00Z"
  };
}

function exportProfile() {
  return {
    id: "profile-1",
    name: "TikTok 竖屏",
    format: "mp4",
    resolution: "1080x1920",
    fps: 30,
    video_bitrate: "8000k",
    audio_policy: "merge_all",
    subtitle_policy: "burn_in",
    config_json: null,
    is_default: true,
    created_at: "2026-04-17T12:00:00Z",
    updated_at: "2026-04-17T12:00:00Z"
  };
}

function renderTask() {
  return {
    id: "render-1",
    project_id: "project-1",
    project_name: "Demo",
    preset: "1080p",
    format: "mp4",
    status: "queued",
    progress: 0,
    output_path: null,
    error_message: null,
    stage: { code: "queued", label: "排队中" },
    output: { path: null, exists: false, size_bytes: null, last_checked_at: "2026-04-17T12:00:00Z", can_open: false },
    failure: { error_code: null, error_message: null, next_action: null, retryable: false },
    started_at: null,
    finished_at: null,
    created_at: "2026-04-17T12:00:00Z",
    updated_at: "2026-04-17T12:00:00Z"
  };
}

function browserInstance(status = "ready") {
  return {
    id: "browser-1",
    workspaceId: "workspace-1",
    name: "默认浏览器",
    profilePath: "D:/tkops/workspaces/main/profiles/default",
    status,
    lastCheckedAt: "2026-04-17T12:00:00Z",
    lastStartedAt: null,
    lastStoppedAt: null,
    errorCode: null,
    errorMessage: null,
    createdAt: "2026-04-17T12:00:00Z",
    updatedAt: "2026-04-17T12:00:00Z"
  };
}

function assetGroup() {
  return {
    id: "group-1",
    name: "主分组",
    parentId: null
  };
}
