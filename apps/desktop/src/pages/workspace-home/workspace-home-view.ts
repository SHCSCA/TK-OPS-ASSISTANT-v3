import { routeIds } from "@/app/router/route-ids";
import {
  createSuggestedWorkspaceAction,
  resolveWorkspaceAction
} from "@/app/actions";
import type {
  AccountReadinessItemDto,
  AccountWorkspaceContextDto
} from "@/types/runtime/accounts";

export type WorkspaceReadinessView = {
  key: "connection" | "knowledge" | "ai";
  label: string;
  icon: string;
  item: AccountReadinessItemDto;
};

export type WorkspaceNextActionView = {
  description: string;
  feedback: string | null;
  label: string;
  to: {
    name: string;
    query?: Record<string, string>;
  };
};

export function createWorkspaceReadinessViews(
  context: AccountWorkspaceContextDto
): WorkspaceReadinessView[] {
  return [
    {
      key: "connection",
      label: "账号连接",
      icon: "link",
      item: context.readiness.connection
    },
    {
      key: "knowledge",
      label: "知识库",
      icon: "library_books",
      item: context.readiness.knowledge
    },
    {
      key: "ai",
      label: "AI 配方",
      icon: "auto_awesome",
      item: context.readiness.ai
    }
  ];
}

export function createWorkspaceNextAction(
  context: AccountWorkspaceContextDto
): WorkspaceNextActionView {
  const suggestion = context.readiness.suggestedAction;
  if (suggestion) {
    const resolution = resolveWorkspaceAction(
      createSuggestedWorkspaceAction(context.account.id, suggestion),
      context.account.id
    );
    if (resolution.ok) {
      return {
        description: "先处理 Runtime 返回的账号就绪建议，再开始内容生产。",
        feedback: null,
        label: suggestion.label,
        to: resolution.to as WorkspaceNextActionView["to"]
      };
    }
    return {
      description: "建议动作未通过安全校验，请从账号设置继续。",
      feedback: resolution.message,
      label: "继续账号设置",
      to: resolution.fallback as WorkspaceNextActionView["to"]
    };
  }

  if (context.readiness.overall === "ready") {
    return {
      description: "账号基础已就绪，可以从选题开始下一条内容。",
      feedback: null,
      label: "进入脚本与选题",
      to: { name: routeIds.accountScriptTopic }
    };
  }

  return {
    description: "继续完善账号连接、知识库或 AI 配方。",
    feedback: null,
    label: "继续账号设置",
    to: { name: routeIds.accountManagement }
  };
}

export function workspaceOverallLabel(
  status: AccountWorkspaceContextDto["readiness"]["overall"]
): string {
  if (status === "ready") return "全部就绪";
  if (status === "blocked") return "存在阻断";
  return "需要处理";
}
