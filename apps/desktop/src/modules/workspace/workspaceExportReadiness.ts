import type { TimelinePrecheckDto, WorkspaceSaveStateDto, WorkspaceTimelineDto } from "@/types/runtime";

export type WorkspaceExportReadinessStatus =
  | "missing_timeline"
  | "unsaved"
  | "precheck_required"
  | "precheck_blocked"
  | "ready";

export type WorkspaceExportReadiness = {
  canRequestExport: boolean;
  description: string;
  status: WorkspaceExportReadinessStatus;
  title: string;
};

export type WorkspaceExportRoute = {
  path: "/renders/export";
  query: {
    from: "workspace";
    projectId: string;
    timelineId: string;
  };
};

export function resolveTimelinePrecheckIssueCount(precheck: TimelinePrecheckDto | null): number {
  if (!precheck) return 0;
  return precheck.issueDetails && precheck.issueDetails.length > 0
    ? precheck.issueDetails.length
    : precheck.issues?.length ?? 0;
}

type ResolveWorkspaceExportReadinessInput = {
  issueCount: number;
  precheck: TimelinePrecheckDto | null;
  saveState: WorkspaceSaveStateDto | null;
  timeline: WorkspaceTimelineDto | null;
};

export function resolveWorkspaceExportReadiness(input: ResolveWorkspaceExportReadinessInput): WorkspaceExportReadiness {
  if (!input.timeline) {
    return {
      canRequestExport: false,
      description: "请先创建或同步 AI 三轨。",
      status: "missing_timeline",
      title: "未创建时间线"
    };
  }

  if (input.saveState?.saved !== true) {
    return {
      canRequestExport: false,
      description: "请先保存时间线。",
      status: "unsaved",
      title: "未保存"
    };
  }

  if (!input.precheck) {
    return {
      canRequestExport: false,
      description: "先执行本地预检。",
      status: "precheck_required",
      title: "预检未执行"
    };
  }

  if (!input.precheck.timelineId || input.precheck.timelineId !== input.timeline.id) {
    return {
      canRequestExport: false,
      description: "当前时间线已变化，请先执行本地预检。",
      status: "precheck_required",
      title: "预检需更新"
    };
  }

  if (input.precheck.status !== "ready" || input.issueCount > 0) {
    return {
      canRequestExport: false,
      description: "先处理预检问题。",
      status: "precheck_blocked",
      title: input.issueCount > 0 ? `发现 ${input.issueCount} 个问题` : "预检需处理"
    };
  }

  return {
    canRequestExport: true,
    description: "可以送往渲染与导出中心。",
    status: "ready",
    title: "可以送往渲染与导出中心"
  };
}

export function buildWorkspaceExportRoute(
  projectId: string | null | undefined,
  timeline: WorkspaceTimelineDto | null
): WorkspaceExportRoute | null {
  if (!projectId || !timeline) return null;
  return {
    path: "/renders/export",
    query: { from: "workspace", projectId, timelineId: timeline.id }
  };
}
