import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkspaceActionStrip from "@/modules/workspace/WorkspaceActionStrip.vue";
import type { WorkspaceExportReadiness } from "@/modules/workspace/workspaceExportReadiness";
import type { TimelinePrecheckDto } from "@/types/runtime";
import type { WorkspacePreviewContext } from "@/modules/workspace/workspacePreviewContext";

describe("WorkspaceActionStrip", () => {
  it("预检 warning 时复用导出门禁语义，不提示准备渲染导出", () => {
    const wrapper = mountActionStrip({
      exportReadiness: {
        canRequestExport: false,
        description: "先处理预检问题。",
        status: "precheck_blocked",
        title: "发现 2 个问题"
      },
      precheck: precheck("warning", ["缺少可用配音轨。", "字幕轨存在空白片段。"])
    });

    expect(wrapper.text()).toContain("发现 2 个问题");
    expect(wrapper.text()).toContain("先处理预检问题。");
    expect(wrapper.text()).not.toContain("准备渲染导出");
    expect(wrapper.text()).not.toContain("导出中心会沿用当前项目和时间线");
  });

  it("时间线变化导致预检过期时提示重新预检", () => {
    const wrapper = mountActionStrip({
      exportReadiness: {
        canRequestExport: false,
        description: "当前时间线已变化，请先执行本地预检。",
        status: "precheck_required",
        title: "预检需更新"
      },
      precheck: precheck("ready", [])
    });

    expect(wrapper.text()).toContain("预检需更新");
    expect(wrapper.text()).toContain("当前时间线已变化，请先执行本地预检。");
    expect(wrapper.text()).not.toContain("准备渲染导出");
  });

  it("预检消息缺失时使用导出门禁标题兜底", () => {
    const wrapper = mountActionStrip({
      exportReadiness: {
        canRequestExport: false,
        description: "先处理预检问题。",
        status: "precheck_blocked",
        title: "预检需处理"
      },
      precheck: {
        timelineId: "timeline-1",
        status: "warning",
        issues: []
      }
    });

    expect(wrapper.text()).toContain("预检需处理");
    expect(wrapper.text()).not.toContain("undefined");
  });

  it("导出门禁 ready 时才提示准备渲染导出", () => {
    const wrapper = mountActionStrip({
      exportReadiness: {
        canRequestExport: true,
        description: "可以送往渲染与导出中心。",
        status: "ready",
        title: "可以送往渲染与导出中心"
      },
      precheck: precheck("ready", [])
    });

    expect(wrapper.text()).toContain("准备渲染导出");
    expect(wrapper.text()).toContain("导出中心会沿用当前项目和时间线。");
  });
});

function mountActionStrip(overrides: {
  exportReadiness: WorkspaceExportReadiness;
  precheck: TimelinePrecheckDto | null;
}) {
  return mount(WorkspaceActionStrip, {
    props: {
      canRedo: false,
      canUndo: false,
      exportReadiness: overrides.exportReadiness,
      isGenerating: false,
      precheck: overrides.precheck,
      previewContext: previewContext()
    }
  });
}

function precheck(status: "ready" | "warning", issues: string[]): TimelinePrecheckDto {
  return {
    timelineId: "timeline-1",
    status,
    message: status === "ready" ? "时间线本地预检通过。" : `时间线本地预检发现 ${issues.length} 个问题。`,
    issues
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
