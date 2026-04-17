import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyReviewSuggestionToScript,
  applyVideoExtractionToProject,
  cancelAutomationRun,
  createBrowserInstance,
  createExecutionBinding,
  createExportProfile,
  extractVideoStructure,
  fetchAutomationRun,
  fetchAutomationRunLogs,
  fetchBrowserInstances,
  fetchExecutionBindings,
  fetchExportProfiles,
  fetchPublishReceipt,
  fetchReviewSuggestions,
  fetchVideoSegments,
  fetchVideoStructure,
  fetchVideoTranscript,
  generateReviewSuggestions,
  removeBrowserInstance,
  removeExecutionBinding,
  retryRenderTask,
  runAccountStatusCheck,
  runVideoSegmentation,
  startVideoTranscription,
  updateReviewSuggestion
} from "@/app/runtime-client";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("Runtime client gap closure 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("为新增接口发送稳定的路径、方法和请求体", async () => {
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

    await runAccountStatusCheck("account-1");
    await fetchBrowserInstances("ws-1");
    await createBrowserInstance({
      workspace_id: "ws-1",
      name: "Chrome Main",
      profile_path: "D:/profiles/chrome-main",
      browser_type: "chrome"
    });
    await removeBrowserInstance("browser-1");
    await fetchExecutionBindings("ws-1");
    await createExecutionBinding({
      account_id: "account-1",
      device_workspace_id: "ws-1",
      browser_instance_id: "browser-1",
      source: "publish"
    });
    await removeExecutionBinding("binding-1");
    await fetchAutomationRun("run-1");
    await fetchAutomationRunLogs("run-1");
    await cancelAutomationRun("run-1");
    await fetchPublishReceipt("plan-1");
    await fetchExportProfiles();
    await createExportProfile({
      name: "竖屏高码率",
      format: "mp4",
      resolution: "1080x1920",
      fps: 30,
      video_bitrate: "12000k",
      audio_policy: "merge_all",
      subtitle_policy: "burn_in"
    });
    await retryRenderTask("render-1");
    await fetchReviewSuggestions("project-1");
    await generateReviewSuggestions("project-1");
    await updateReviewSuggestion("suggestion-1", { status: "dismissed" });
    await applyReviewSuggestionToScript("suggestion-1");
    await startVideoTranscription("video-1");
    await fetchVideoTranscript("video-1");
    await runVideoSegmentation("video-1");
    await fetchVideoSegments("video-1");
    await extractVideoStructure("video-1");
    await fetchVideoStructure("video-1");
    await applyVideoExtractionToProject("extract-1");

    expect(calls).toEqual([
      { path: "/api/accounts/account-1/status-check", method: "POST", body: undefined },
      { path: "/api/devices/browser-instances?workspace_id=ws-1", method: "GET", body: undefined },
      {
        path: "/api/devices/browser-instances",
        method: "POST",
        body: {
          workspace_id: "ws-1",
          name: "Chrome Main",
          profile_path: "D:/profiles/chrome-main",
          browser_type: "chrome"
        }
      },
      { path: "/api/devices/browser-instances/browser-1", method: "DELETE", body: undefined },
      { path: "/api/devices/bindings?device_workspace_id=ws-1", method: "GET", body: undefined },
      {
        path: "/api/devices/bindings",
        method: "POST",
        body: {
          account_id: "account-1",
          device_workspace_id: "ws-1",
          browser_instance_id: "browser-1",
          source: "publish"
        }
      },
      { path: "/api/devices/bindings/binding-1", method: "DELETE", body: undefined },
      { path: "/api/automation/runs/run-1", method: "GET", body: undefined },
      { path: "/api/automation/runs/run-1/logs", method: "GET", body: undefined },
      { path: "/api/automation/runs/run-1/cancel", method: "POST", body: undefined },
      { path: "/api/publishing/plans/plan-1/receipt", method: "GET", body: undefined },
      { path: "/api/renders/profiles", method: "GET", body: undefined },
      {
        path: "/api/renders/profiles",
        method: "POST",
        body: {
          name: "竖屏高码率",
          format: "mp4",
          resolution: "1080x1920",
          fps: 30,
          video_bitrate: "12000k",
          audio_policy: "merge_all",
          subtitle_policy: "burn_in"
        }
      },
      { path: "/api/renders/tasks/render-1/retry", method: "POST", body: undefined },
      { path: "/api/review/projects/project-1/suggestions", method: "GET", body: undefined },
      { path: "/api/review/projects/project-1/suggestions/generate", method: "POST", body: undefined },
      {
        path: "/api/review/suggestions/suggestion-1",
        method: "PATCH",
        body: { status: "dismissed" }
      },
      {
        path: "/api/review/suggestions/suggestion-1/apply-to-script",
        method: "POST",
        body: undefined
      },
      { path: "/api/video-deconstruction/videos/video-1/transcribe", method: "POST", body: undefined },
      { path: "/api/video-deconstruction/videos/video-1/transcript", method: "GET", body: undefined },
      { path: "/api/video-deconstruction/videos/video-1/segment", method: "POST", body: undefined },
      { path: "/api/video-deconstruction/videos/video-1/segments", method: "GET", body: undefined },
      {
        path: "/api/video-deconstruction/videos/video-1/extract-structure",
        method: "POST",
        body: undefined
      },
      { path: "/api/video-deconstruction/videos/video-1/structure", method: "GET", body: undefined },
      {
        path: "/api/video-deconstruction/extractions/extract-1/apply-to-project",
        method: "POST",
        body: undefined
      }
    ]);
  });
});

function sampleResponseFor(path: string, method: string): unknown {
  if (path.includes("/status-check")) {
    return { id: "account-1", status: "active", updatedAt: now(), providerStatus: "pending_provider" };
  }
  if (path.startsWith("/api/devices/browser-instances") && method === "GET") return [browserInstance()];
  if (path.startsWith("/api/devices/browser-instances")) return browserInstance();
  if (path.startsWith("/api/devices/bindings") && method === "GET") return [executionBinding()];
  if (path.startsWith("/api/devices/bindings")) return executionBinding();
  if (path.endsWith("/logs")) return { run_id: "run-1", log_text: "line-1\nline-2", lines: ["line-1", "line-2"] };
  if (path.endsWith("/cancel") && path.startsWith("/api/automation")) return automationRun("cancelled");
  if (path.startsWith("/api/automation/runs")) return automationRun();
  if (path.endsWith("/receipt")) return publishReceipt();
  if (path === "/api/renders/profiles" && method === "GET") return [exportProfile()];
  if (path === "/api/renders/profiles" && method === "POST") return exportProfile("profile-2", false);
  if (path.endsWith("/retry")) return renderTask("queued", 0);
  if (path.endsWith("/suggestions/generate")) {
    return {
      project_id: "project-1",
      status: "done",
      message: "建议生成完成",
      generated_count: 2,
      generated_at: now()
    };
  }
  if (path.endsWith("/apply-to-script")) {
    return {
      project_id: "project-1",
      suggestion_id: "suggestion-1",
      script_revision: 2,
      status: "applied",
      message: "建议已应用到脚本"
    };
  }
  if (path.startsWith("/api/review/suggestions/")) return reviewSuggestion("dismissed");
  if (path.endsWith("/suggestions")) return [reviewSuggestion()];
  if (path.endsWith("/transcribe") || path.endsWith("/transcript")) return videoTranscript();
  if (path.endsWith("/segment") || path.endsWith("/segments")) return [videoSegment()];
  if (path.endsWith("/extract-structure") || path.endsWith("/structure")) return videoStructure();
  if (path.endsWith("/apply-to-project")) {
    return {
      projectId: "project-1",
      extractionId: "extract-1",
      scriptRevision: 2,
      status: "applied",
      message: "视频拆解结果已回流到脚本"
    };
  }
  return {};
}

function now() {
  return "2026-04-17T10:00:00Z";
}

function browserInstance() {
  return {
    id: "browser-1",
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

function executionBinding() {
  return {
    id: "binding-1",
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

function exportProfile(id = "profile-1", isDefault = true) {
  return {
    id,
    name: isDefault ? "默认竖屏导出" : "竖屏高码率",
    format: "mp4",
    resolution: "1080x1920",
    fps: 30,
    video_bitrate: "8000k",
    audio_policy: "merge_all",
    subtitle_policy: "burn_in",
    config_json: null,
    is_default: isDefault,
    created_at: now(),
    updated_at: now()
  };
}

function renderTask(status: string, progress: number) {
  return {
    id: "render-1",
    project_id: "project-1",
    project_name: "Demo",
    preset: "1080p",
    format: "mp4",
    status,
    progress,
    output_path: null,
    error_message: null,
    started_at: null,
    finished_at: null,
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

function videoTranscript() {
  return {
    id: "transcript-1",
    videoId: "video-1",
    language: "zh-CN",
    text: null,
    status: "pending_provider",
    createdAt: now(),
    updatedAt: now()
  };
}

function videoSegment() {
  return {
    id: "segment-1",
    videoId: "video-1",
    segmentIndex: 0,
    startMs: 0,
    endMs: 30000,
    label: "intro",
    transcriptText: null,
    metadataJson: null,
    createdAt: now()
  };
}

function videoStructure() {
  return {
    id: "extract-1",
    videoId: "video-1",
    status: "pending_provider",
    scriptJson: null,
    storyboardJson: null,
    createdAt: now(),
    updatedAt: now()
  };
}
