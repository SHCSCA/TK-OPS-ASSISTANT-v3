import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import WorkspaceInspector from "@/modules/workspace/WorkspaceInspector.vue";
import { buildWorkspaceExportRoute } from "@/modules/workspace/workspaceExportReadiness";
import type {
  TimelinePrecheckDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";
import type { WorkspacePreviewContext } from "@/modules/workspace/workspacePreviewContext";

describe("M05 导出就绪卡", () => {
  it("导出就绪禁用态由语义布尔控制，不依赖中文标题比较", () => {
    const source = readFileSync(
      join(process.cwd(), "src/modules/workspace/WorkspaceInspector.vue"),
      "utf-8"
    );

    expect(source).toContain("canRequestExport");
    expect(source).not.toContain('exportReadinessTitle.value !== "可以送往渲染与导出中心"');
  });

  it("未创建时间线、未保存、未预检和预检问题都会禁用入口且不 emit", async () => {
    const cases = [
      {
        props: { timeline: null, saveState: null, precheck: null },
        text: "先创建或同步 AI 三轨"
      },
      {
        props: { saveState: saveState(false), precheck: null },
        text: "先保存时间线"
      },
      {
        props: { saveState: saveState(true), precheck: null },
        text: "先执行本地预检"
      },
      {
        props: { saveState: saveState(true), precheck: precheck("warning", ["缺少可用配音轨。", "字幕轨存在空白片段。"]) },
        text: "发现 2 个问题"
      },
      {
        props: { saveState: saveState(true), precheck: precheck("warning", []) },
        text: "预检需处理"
      },
      {
        props: { saveState: saveState(true), precheck: precheck("ready", [], "stale-timeline") },
        text: "先执行本地预检"
      },
      {
        props: { saveState: saveState(true), precheck: precheckWithoutTimelineId() },
        text: "先执行本地预检"
      }
    ];

    for (const item of cases) {
      const wrapper = mountInspector(item.props);
      const readiness = wrapper.get('[data-testid="workspace-export-readiness"]');

      expect(readiness.text()).toContain(item.text);
      expect(wrapper.get('[data-testid="workspace-export-readiness-action"]').attributes("disabled")).toBeDefined();

      await wrapper.get('[data-testid="workspace-export-readiness-action"]').trigger("click");

      expect(wrapper.emitted("request-export")).toBeUndefined();
    }
  });

  it("预检通过时启用入口并 emit", async () => {
    const wrapper = mountInspector({
      saveState: saveState(true),
      precheck: precheck("ready", [])
    });

    expect(wrapper.get('[data-testid="workspace-export-readiness"]').text()).toContain("可以送往渲染与导出中心");
    expect(wrapper.get('[data-testid="workspace-export-readiness-action"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-testid="workspace-export-readiness-action"]').trigger("click");

    expect(wrapper.emitted("request-export")).toHaveLength(1);
  });

  it("选中片段后显示当前片段操作并可定位播放头", async () => {
    const wrapper = mountInspector({
      precheck: precheck("ready", []),
      previewContext: {
        ...previewContext(),
        previewMode: "media",
        mediaKind: "video",
        mediaUrl: "http://127.0.0.1:8000/media/clip.mp4"
      },
      saveState: saveState(true),
      selectedClip: timelineClip()
    });

    const actions = wrapper.get('[data-testid="workspace-inspector-clip-actions"]');

    expect(actions.text()).toContain("从片段起点检查");
    expect(actions.text()).toContain("S02 · 配音");
    expect(actions.text()).toContain("起点 00:02");
    expect(actions.text()).toContain("已保存");
    expect(actions.text()).toContain("通过");
    expect(actions.text()).toContain("可播放");

    await wrapper.get('[data-testid="workspace-inspector-seek-clip-start"]').trigger("click");

    expect(wrapper.emitted("seek-clip-start")).toHaveLength(1);
  });

  it("导出路由 helper 生成渲染与导出中心 query，缺少上下文时返回空", () => {
    expect(buildWorkspaceExportRoute("project-1", workspaceTimeline())).toEqual({
      path: "/renders/export",
      query: {
        from: "workspace",
        projectId: "project-1",
        timelineId: "timeline-1"
      }
    });
    expect(buildWorkspaceExportRoute("", workspaceTimeline())).toBeNull();
    expect(buildWorkspaceExportRoute("project-1", null)).toBeNull();
  });
});

function mountInspector(overrides: Partial<ReturnType<typeof inspectorProps>> = {}) {
  return mount(WorkspaceInspector, {
    props: inspectorProps(overrides)
  });
}

function inspectorProps(overrides: Partial<{
  precheck: TimelinePrecheckDto | null;
  previewContext: WorkspacePreviewContext;
  saveState: WorkspaceSaveStateDto | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}> = {}) {
  const timeline = Object.prototype.hasOwnProperty.call(overrides, "timeline")
    ? overrides.timeline ?? null
    : workspaceTimeline();

  return {
    assemblyState: null,
    blockedMessage: null,
    errorMessage: null,
    lastCommandResult: null,
    precheck: overrides.precheck ?? null,
    previewContext: overrides.previewContext ?? previewContext(),
    saveState: overrides.saveState ?? saveState(true),
    selectedClip: overrides.selectedClip ?? null,
    selectedTrack: null,
    status: "ready" as const,
    timeline
  };
}

function workspaceTimeline(tracks: WorkspaceTimelineTrackDto[] = []): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function saveState(saved: boolean): WorkspaceSaveStateDto {
  return {
    saved,
    updatedAt: now(),
    source: "test",
    message: saved ? "已保存时间线。" : "保存失败。"
  };
}

function precheck(status: "ready" | "warning", issues: string[], timelineId = "timeline-1"): TimelinePrecheckDto {
  return {
    timelineId,
    status,
    message: status === "ready" ? "时间线本地预检通过。" : `时间线本地预检发现 ${issues.length} 个问题。`,
    issues
  };
}

function precheckWithoutTimelineId(): TimelinePrecheckDto {
  return {
    status: "ready",
    message: "时间线本地预检通过。",
    issues: []
  };
}

function timelineClip(): WorkspaceTimelineClipDto {
  return {
    id: "clip-voice-2",
    trackId: "managed-audio-voice",
    sourceType: "voice_track",
    sourceId: "voice-2",
    label: "S02 · 配音",
    startMs: 2400,
    durationMs: 3600,
    inPointMs: 0,
    outPointMs: null,
    status: "ready",
    metadata: {
      sourceKind: "voice_track",
      sourceRevision: 1,
      segmentIndex: 1,
      segmentId: "S02",
      text: "Now my room feels like a 5-star studio.",
      visualPrompt: null
    }
  };
}

function previewContext(): WorkspacePreviewContext {
  return {
    captionText: "等待片段",
    clip: null,
    currentTimeLabel: "当前时间：00:00",
    description: "移动播放头或选择片段后查看具体上下文。",
    detailText: "当前片段：未命中",
    headline: "预览舞台",
    kind: "empty",
    manifestSummary: null,
    mediaKind: null,
    mediaUrl: null,
    previewMode: "structure",
    rangeLabel: "未命中片段",
    runtimePreviewErrorMessage: null,
    runtimePreviewUrl: null,
    sourceLabel: "未选择",
    sourceType: "none",
    statusLabel: "未选择",
    summaryText: "暂无可展示片段",
    truthDescription: "创建时间线草稿后，可以在这里检查画面、字幕和节奏。",
    truthLabel: "分镜预览",
    track: null
  };
}

function now() {
  return "2026-04-17T10:00:00Z";
}
