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
      deviceWorkspaceId: "workspace-1",
      browserInstanceId: "browser-1"
    });
    await runtimeClient.fetchWorkspaceLogs("workspace-1", "cursor-1");
    await runtimeClient.pauseAutomationTask("auto-1");
    await runtimeClient.resumeAutomationTask("auto-1");
    await runtimeClient.fetchPublishingCalendar("2026-04-17", "2026-04-23");
    await runtimeClient.fetchPublishReceipts("plan-1");
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
          deviceWorkspaceId: "workspace-1",
          browserInstanceId: "browser-1"
        }
      },
      {
        path: "/api/devices/workspaces/workspace-1/logs?cursor=cursor-1",
        method: "GET",
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
        path: "/api/publishing/calendar?from=2026-04-17&to=2026-04-23",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/publishing/plans/plan-1/receipts",
        method: "GET",
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
  if (path.includes("/binding")) {
    return {
      id: "binding-1",
      accountId: "account-1",
      deviceWorkspaceId: "workspace-1",
      browserInstanceId: "browser-1",
      status: "active"
    };
  }
  if (path.includes("/logs")) {
    return {
      items: [{ timestamp: "2026-04-17T12:00:00Z", level: "INFO", message: "workspace.ready" }],
      nextCursor: null
    };
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
    return [{ date: "2026-04-17", plans: 1 }];
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

function assetGroup() {
  return {
    id: "group-1",
    name: "主分组",
    parentId: null
  };
}
