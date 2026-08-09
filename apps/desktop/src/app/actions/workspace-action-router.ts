import type { RouteLocationRaw } from "vue-router";

import { routeIds, type RouteId } from "@/app/router/route-ids";
import type { AccountSuggestedActionDto } from "@/types/runtime/accounts";

export type WorkspaceActionKey =
  | "open_connection"
  | "open_environment"
  | "open_knowledge"
  | "open_ai_recipe"
  | "run_health_check"
  | "view_log";

export type WorkspaceAction = {
  version: 1;
  action: WorkspaceActionKey;
  accountId: string;
  routeId: RouteId;
  wizardStep?: string;
  environmentId?: string;
  taskId?: string;
  logId?: string;
  returnTo?: {
    routeId: RouteId;
    query?: Record<string, string>;
  };
};

export type WorkspaceActionResolution =
  | {
      ok: true;
      action: WorkspaceAction;
      to: RouteLocationRaw;
    }
  | {
      ok: false;
      code:
        | "ACTION_INVALID"
        | "ACTION_ACCOUNT_MISMATCH"
        | "ACTION_ROUTE_FORBIDDEN";
      message: string;
      fallback: RouteLocationRaw;
    };

const stableIdPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const routeIdSet = new Set<RouteId>(Object.values(routeIds));
const routePolicy: Record<WorkspaceActionKey, ReadonlySet<RouteId>> = {
  open_connection: new Set([routeIds.accountManagement]),
  open_environment: new Set([routeIds.accountManagement]),
  open_knowledge: new Set([routeIds.accountStrategyKnowledge]),
  open_ai_recipe: new Set([routeIds.aiSystemSettings]),
  run_health_check: new Set([routeIds.accountManagement]),
  view_log: new Set([
    routeIds.accountManagement,
    routeIds.aiSystemSettings
  ])
};

export function createSuggestedWorkspaceAction(
  accountId: string,
  suggestion: AccountSuggestedActionDto
): WorkspaceAction {
  return {
    version: 1,
    action: suggestion.actionKey,
    accountId,
    routeId: suggestion.routeId as RouteId,
    ...(suggestion.section ? { wizardStep: suggestion.section } : {}),
    ...(suggestion.taskId ? { taskId: suggestion.taskId } : {})
  };
}

export function resolveWorkspaceAction(
  input: unknown,
  expectedAccountId: string
): WorkspaceActionResolution {
  const fallback = accountFallback(expectedAccountId);
  if (!isRecord(input) || input.version !== 1) {
    return invalid("ACTION_INVALID", "建议动作格式无效，已停止跳转。", fallback);
  }
  if (!isStableId(expectedAccountId) || input.accountId !== expectedAccountId) {
    return invalid(
      "ACTION_ACCOUNT_MISMATCH",
      "建议动作不属于当前账号，已停止跳转。",
      fallback
    );
  }
  if (
    !isWorkspaceActionKey(input.action)
    || !isRouteId(input.routeId)
    || !routePolicy[input.action].has(input.routeId)
  ) {
    return invalid(
      "ACTION_ROUTE_FORBIDDEN",
      "建议动作目标不在允许范围内，已停止跳转。",
      fallback
    );
  }
  const optionalFields = [
    input.wizardStep,
    input.environmentId,
    input.taskId,
    input.logId
  ];
  if (optionalFields.some((value) => value !== undefined && !isStableId(value))) {
    return invalid("ACTION_INVALID", "建议动作参数无效，已停止跳转。", fallback);
  }
  const returnTo = parseReturnTo(input.returnTo);
  if (input.returnTo !== undefined && returnTo === null) {
    return invalid("ACTION_ROUTE_FORBIDDEN", "返回目标不在允许范围内。", fallback);
  }

  const action: WorkspaceAction = {
    version: 1,
    action: input.action,
    accountId: expectedAccountId,
    routeId: input.routeId,
    ...(typeof input.wizardStep === "string"
      ? { wizardStep: input.wizardStep }
      : {}),
    ...(typeof input.environmentId === "string"
      ? { environmentId: input.environmentId }
      : {}),
    ...(typeof input.taskId === "string" ? { taskId: input.taskId } : {}),
    ...(typeof input.logId === "string" ? { logId: input.logId } : {}),
    ...(returnTo ? { returnTo } : {})
  };
  return { ok: true, action, to: actionLocation(action) };
}

function actionLocation(action: WorkspaceAction): RouteLocationRaw {
  const query: Record<string, string> = {
    account: action.accountId,
    source: "workspace-action"
  };
  if (action.wizardStep) query.section = action.wizardStep;
  if (action.environmentId) query.environment = action.environmentId;
  if (action.taskId) query.taskId = action.taskId;
  if (action.logId) query.logId = action.logId;
  if (action.action === "open_connection") query.action = "continue";
  if (action.action === "run_health_check") query.action = "health";
  return { name: action.routeId, query };
}

function parseReturnTo(value: unknown): WorkspaceAction["returnTo"] | null {
  if (value === undefined) return undefined;
  if (!isRecord(value) || !isRouteId(value.routeId)) return null;
  if (value.routeId === routeIds.setupLicenseWizard) return null;
  if (value.query === undefined) return { routeId: value.routeId };
  if (!isRecord(value.query)) return null;
  const entries = Object.entries(value.query);
  if (
    entries.length > 12
    || entries.some(
      ([key, item]) => !isStableId(key) || typeof item !== "string" || item.length > 256
    )
  ) {
    return null;
  }
  const query: Record<string, string> = {};
  for (const [key, item] of entries) query[key] = item as string;
  return { routeId: value.routeId, query };
}

function accountFallback(accountId: string): RouteLocationRaw {
  return {
    name: routeIds.accountManagement,
    query: isStableId(accountId) ? { account: accountId } : {}
  };
}

function invalid(
  code: Extract<WorkspaceActionResolution, { ok: false }>["code"],
  message: string,
  fallback: RouteLocationRaw
): WorkspaceActionResolution {
  return { ok: false, code, message, fallback };
}

function isWorkspaceActionKey(value: unknown): value is WorkspaceActionKey {
  return typeof value === "string" && value in routePolicy;
}

function isRouteId(value: unknown): value is RouteId {
  return typeof value === "string" && routeIdSet.has(value as RouteId);
}

function isStableId(value: unknown): value is string {
  return typeof value === "string" && stableIdPattern.test(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
