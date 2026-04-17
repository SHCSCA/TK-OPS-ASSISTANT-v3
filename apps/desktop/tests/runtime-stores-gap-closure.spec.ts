import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAutomationStore } from "@/stores/automation";
import { useDeviceWorkspacesStore } from "@/stores/device-workspaces";
import { usePublishingStore } from "@/stores/publishing";
import { useRendersStore } from "@/stores/renders";
import { useReviewStore } from "@/stores/review";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("Gap closure stores Runtime 行为", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("设备 store 维护浏览器实例和绑定状态", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/devices/workspaces" && method === "GET") return okJsonResponse([workspace()]);
        if (path === "/api/devices/browser-instances?workspace_id=ws-1") return okJsonResponse([browserInstance()]);
        if (path === "/api/devices/browser-instances" && method === "POST") {
          return okJsonResponse(browserInstance("browser-2"));
        }
        if (path === "/api/devices/browser-instances/browser-1" && method === "DELETE") {
          return okJsonResponse({ deleted: true });
        }
        if (path === "/api/devices/bindings?device_workspace_id=ws-1") {
          return okJsonResponse([binding()]);
        }
        if (path === "/api/devices/bindings" && method === "POST") return okJsonResponse(binding("binding-2"));
        if (path === "/api/devices/bindings/binding-1" && method === "DELETE") {
          return okJsonResponse({ deleted: true });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useDeviceWorkspacesStore();
    await store.loadWorkspaces();
    await store.loadBrowserInstances("ws-1");
    await store.addBrowserInstance({
      workspace_id: "ws-1",
      name: "Chrome Backup",
      profile_path: "D:/profiles/chrome-backup",
      browser_type: "chrome"
    });
    await store.removeBrowserInstance("browser-1");
    await store.loadBindings("ws-1");
    await store.addBinding({
      account_id: "account-1",
      device_workspace_id: "ws-1",
      browser_instance_id: "browser-1",
      source: "publish"
    });
    await store.removeBinding("binding-1");

    expect(store.browserInstancesByWorkspaceId["ws-1"].map((item) => item.id)).toContain("browser-2");
    expect(store.bindingsByWorkspaceId["ws-1"].map((item) => item.id)).toContain("binding-2");
  });

  it("自动化、发布、渲染和复盘 store 暴露新增动作", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/automation/tasks" && method === "GET") return okJsonResponse([automationTask()]);
        if (path === "/api/automation/runs/run-1") return okJsonResponse(automationRun());
        if (path === "/api/automation/runs/run-1/logs") {
          return okJsonResponse({ run_id: "run-1", log_text: "line-1\nline-2", lines: ["line-1", "line-2"] });
        }
        if (path === "/api/automation/runs/run-1/cancel") return okJsonResponse(automationRun("cancelled"));
        if (path === "/api/publishing/plans" && method === "GET") return okJsonResponse([publishPlan()]);
        if (path === "/api/publishing/plans/plan-1/receipt") return okJsonResponse(publishReceipt());
        if (path === "/api/renders/tasks" && method === "GET") return okJsonResponse([renderTask()]);
        if (path === "/api/renders/profiles") return okJsonResponse([exportProfile()]);
        if (path === "/api/renders/tasks/render-1/retry") return okJsonResponse(renderTask("queued", 0));
        if (path === "/api/review/projects/project-1/summary") return okJsonResponse(reviewSummary());
        if (path === "/api/review/projects/project-1/suggestions") return okJsonResponse([reviewSuggestion()]);
        if (path === "/api/review/projects/project-1/suggestions/generate") {
          return okJsonResponse({
            project_id: "project-1",
            status: "done",
            message: "建议生成完成",
            generated_count: 1,
            generated_at: now()
          });
        }
        if (path === "/api/review/suggestions/suggestion-1" && method === "PATCH") {
          return okJsonResponse(reviewSuggestion("dismissed"));
        }
        if (path === "/api/review/suggestions/suggestion-1/apply-to-script" && method === "POST") {
          return okJsonResponse({
            project_id: "project-1",
            suggestion_id: "suggestion-1",
            script_revision: 2,
            status: "applied",
            message: "建议已应用到脚本"
          });
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const automation = useAutomationStore();
    await automation.loadTasks();
    await automation.loadRun("run-1");
    await automation.loadRunLogs("run-1");
    await automation.cancelRun("run-1");
    expect(automation.runDetailsById["run-1"]?.status).toBe("cancelled");
    expect(automation.runLogsById["run-1"]?.lines).toHaveLength(2);

    const publishing = usePublishingStore();
    await publishing.loadPlans();
    await publishing.loadReceipt("plan-1");
    expect(publishing.receiptsByPlanId["plan-1"]?.status).toBe("manual_required");

    const renders = useRendersStore();
    await renders.loadTasks();
    await renders.loadProfiles();
    await renders.retry("render-1");
    expect(renders.profiles).toHaveLength(1);
    expect(renders.tasks[0]?.status).toBe("queued");

    const review = useReviewStore();
    await review.loadSummary("project-1");
    await review.loadSuggestions("project-1");
    await review.generateSuggestions("project-1");
    await review.updateSuggestion("suggestion-1", { status: "dismissed" });
    await review.applySuggestionToScript("suggestion-1");
    expect(review.suggestions[0]?.status).toBe("applied");
    expect(review.lastGenerateSuggestionsResult?.generated_count).toBe(1);
  });
});

function now() {
  return "2026-04-17T10:00:00Z";
}

function workspace() {
  return {
    id: "ws-1",
    name: "Main",
    root_path: "D:/tkops/workspaces/main",
    status: "online",
    error_count: 0,
    last_used_at: null,
    created_at: now(),
    updated_at: now()
  };
}

function browserInstance(id = "browser-1") {
  return {
    id,
    workspace_id: "ws-1",
    name: "Chrome Main",
    profile_path: "D:/profiles/chrome-main",
    browser_type: "chrome",
    status: "stopped",
    last_seen_at: null,
    created_at: now(),
    updated_at: now()
  };
}

function binding(id = "binding-1") {
  return {
    id,
    account_id: "account-1",
    device_workspace_id: "ws-1",
    browser_instance_id: "browser-1",
    status: "active",
    source: "publish",
    metadata_json: null,
    created_at: now(),
    updated_at: now()
  };
}

function automationTask() {
  return {
    id: "task-1",
    name: "同步发布状态",
    type: "sync",
    enabled: true,
    cron_expr: null,
    last_run_at: null,
    last_run_status: null,
    run_count: 0,
    config_json: null,
    created_at: now(),
    updated_at: now()
  };
}

function automationRun(status = "running") {
  return {
    id: "run-1",
    task_id: "task-1",
    status,
    started_at: now(),
    finished_at: status === "cancelled" ? now() : null,
    log_text: "line-1\nline-2",
    created_at: now()
  };
}

function publishPlan() {
  return {
    id: "plan-1",
    title: "发布计划",
    account_id: null,
    account_name: "Creator A",
    project_id: "project-1",
    video_asset_id: null,
    status: "submitted",
    scheduled_at: null,
    submitted_at: now(),
    published_at: null,
    error_message: null,
    precheck_result_json: null,
    created_at: now(),
    updated_at: now()
  };
}

function publishReceipt() {
  return {
    id: "receipt-1",
    plan_id: "plan-1",
    status: "manual_required",
    external_url: null,
    error_message: null,
    completed_at: now(),
    created_at: now()
  };
}

function exportProfile() {
  return {
    id: "profile-1",
    name: "默认竖屏导出",
    format: "mp4",
    resolution: "1080x1920",
    fps: 30,
    video_bitrate: "8000k",
    audio_policy: "merge_all",
    subtitle_policy: "burn_in",
    config_json: null,
    is_default: true,
    created_at: now(),
    updated_at: now()
  };
}

function renderTask(status = "failed", progress = 100) {
  return {
    id: "render-1",
    project_id: "project-1",
    project_name: "Demo",
    preset: "1080p",
    format: "mp4",
    status,
    progress,
    output_path: null,
    error_message: status === "failed" ? "编码失败" : null,
    started_at: null,
    finished_at: null,
    created_at: now(),
    updated_at: now()
  };
}

function reviewSummary() {
  return {
    id: "review-1",
    project_id: "project-1",
    project_name: "Demo",
    total_views: 0,
    total_likes: 0,
    total_comments: 0,
    avg_watch_time_sec: 0,
    completion_rate: 0,
    suggestions: [],
    last_analyzed_at: null,
    created_at: now(),
    updated_at: now()
  };
}

function reviewSuggestion(status = "pending") {
  return {
    id: "suggestion-1",
    code: "hook_first_3s",
    category: "内容结构",
    title: "强化前三秒钩子",
    description: "开头需要更快进入冲突和收益点。",
    priority: "high",
    status,
    actionLabel: "应用到脚本",
    sourceType: "script",
    sourceId: "script-1",
    createdAt: now()
  };
}
