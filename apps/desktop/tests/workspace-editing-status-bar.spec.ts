import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceEditingStatusBar from "@/modules/workspace/WorkspaceEditingStatusBar.vue";
import type { WorkspacePreviewContext } from "@/modules/workspace/workspacePreviewContext";
import type { TimelinePrecheckDto, WorkspaceAICommandResultDto, WorkspaceSaveStateDto } from "@/types/runtime";
import type { TaskInfo } from "@/types/task-events";

describe("M05 持续状态栏", () => {
  it("展示剪辑时必须持续可见的时间码、选择、保存、预检、预览和任务状态", () => {
    const wrapper = mount(WorkspaceEditingStatusBar, {
      props: {
        activeTask: taskInfo(),
        isPlaying: true,
        lastCommandResult: null,
        playheadMs: 4200,
        precheck: precheck(),
        previewContext: previewContext(),
        saveState: saveState(),
        selectionLabel: "片段：S02 · 配音"
      }
    });

    expect(wrapper.get('[data-testid="workspace-status-playhead"]').text()).toContain("00:04");
    expect(wrapper.get('[data-testid="workspace-status-selection"]').text()).toContain("片段：S02 · 配音");
    expect(wrapper.get('[data-testid="workspace-status-save"]').text()).toContain("已保存");
    expect(wrapper.get('[data-testid="workspace-status-precheck"]').text()).toContain("预检通过");
    expect(wrapper.get('[data-testid="workspace-status-preview"]').text()).toContain("真实媒体");
    expect(wrapper.get('[data-testid="workspace-status-task"]').text()).toContain("智能粗剪 35%");
    expect(wrapper.text()).toContain("播放中");
  });

  it("任务进度超出边界时必须夹紧展示，避免状态栏出现异常百分比", () => {
    const wrapper = mount(WorkspaceEditingStatusBar, {
      props: defaultProps({
        activeTask: {
          ...taskInfo(),
          progress: 135.7
        }
      })
    });

    expect(wrapper.get('[data-testid="workspace-status-task"]').text()).toContain("智能粗剪 100%");
  });

  it("没有活跃任务时必须保留最近一次 AI 命令终态", () => {
    const wrapper = mount(WorkspaceEditingStatusBar, {
      props: defaultProps({
        activeTask: null,
        lastCommandResult: commandResult("failed")
      })
    });

    const taskStatus = wrapper.get('[data-testid="workspace-status-task"]');
    expect(taskStatus.text()).toContain("智能粗剪失败");
    expect(taskStatus.attributes("data-tone")).toBe("danger");
  });
});

function defaultProps(
  overrides: Partial<InstanceType<typeof WorkspaceEditingStatusBar>["$props"]> = {}
): InstanceType<typeof WorkspaceEditingStatusBar>["$props"] {
  return {
    activeTask: taskInfo(),
    isPlaying: true,
    lastCommandResult: null,
    playheadMs: 4200,
    precheck: precheck(),
    previewContext: previewContext(),
    saveState: saveState(),
    selectionLabel: "片段：S02 · 配音",
    ...overrides
  };
}

function saveState(): WorkspaceSaveStateDto {
  return {
    saved: true,
    updatedAt: "2026-04-17T10:00:00Z",
    source: "manual_save",
    message: "已保存当前时间线。"
  };
}

function precheck(): TimelinePrecheckDto {
  return {
    timelineId: "timeline-1",
    status: "ready",
    message: "时间线本地预检通过。",
    issues: []
  };
}

function taskInfo(): TaskInfo {
  return {
    id: "task-1",
    task_type: "ai-workspace-command",
    project_id: "project-1",
    status: "running",
    progress: 35,
    message: "智能粗剪正在生成。",
    created_at: "2026-04-17T10:00:00Z",
    updated_at: "2026-04-17T10:00:01Z"
  };
}

function commandResult(status: WorkspaceAICommandResultDto["status"]): WorkspaceAICommandResultDto {
  return {
    status,
    task: null,
    message: "AI 调用失败，请检查能力配置。"
  };
}

function previewContext(): WorkspacePreviewContext {
  return {
    captionText: "Now my room feels like a 5-star studio.",
    clip: null,
    currentTimeLabel: "当前时间：00:04",
    description: "可播放素材。",
    detailText: "当前片段：S02 · 配音",
    headline: "S02",
    kind: "video",
    manifestSummary: null,
    mediaInfoText: "MIME：video/mp4",
    mediaKind: "video",
    mediaUrl: "http://127.0.0.1:8000/media/s02.mp4",
    previewMode: "media",
    rangeLabel: "00:04-00:08",
    runtimePreviewErrorMessage: null,
    runtimePreviewUrl: null,
    sourceLabel: "资产中心素材",
    sourceType: "asset",
    statusLabel: "已就绪",
    summaryText: "画面来源：资产中心素材",
    truthDescription: "正在播放已导入的本地素材。",
    truthLabel: "素材预览",
    track: null
  };
}
