import type { LocationQuery } from "vue-router";

import type { CurrentProjectContext } from "@/types/runtime";

export type RenderWorkspaceHandoffStatus = "ready" | "missing-timeline" | "project-mismatch";
export type RenderWorkspaceHandoffTone = "success" | "warning";

export type RenderWorkspaceHandoffView = {
  status: RenderWorkspaceHandoffStatus;
  tone: RenderWorkspaceHandoffTone;
  title: string;
  description: string;
  projectName: string;
  projectId: string;
  currentProjectId: string;
  timelineId: string | null;
  canCreateFromHandoff: boolean;
};

export function buildRenderWorkspaceHandoff(
  query: LocationQuery,
  currentProject: CurrentProjectContext | null
): RenderWorkspaceHandoffView | null {
  if (readQueryValue(query.from) !== "workspace" || !currentProject) {
    return null;
  }

  const projectId = readQueryValue(query.projectId);
  const timelineId = readQueryValue(query.timelineId);
  const currentProjectId = currentProject.projectId;
  const projectName = currentProject.projectName;

  if (projectId !== currentProjectId) {
    return {
      status: "project-mismatch",
      tone: "warning",
      title: "项目上下文不一致",
      description: "传入项目与当前项目不一致，请回到 AI 剪辑工作台重新进入导出链路。",
      projectName,
      projectId,
      currentProjectId,
      timelineId,
      canCreateFromHandoff: false
    };
  }

  if (!timelineId) {
    return {
      status: "missing-timeline",
      tone: "warning",
      title: "交接信息不完整",
      description: "回到 AI 剪辑工作台重新执行导出前预检。",
      projectName,
      projectId,
      currentProjectId,
      timelineId: null,
      canCreateFromHandoff: false
    };
  }

  return {
    status: "ready",
    tone: "success",
    title: "来自 AI 剪辑工作台",
    description: "可以继续配置导出任务。",
    projectName,
    projectId,
    currentProjectId,
    timelineId,
    canCreateFromHandoff: true
  };
}

function readQueryValue(value: LocationQuery[string]): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}
