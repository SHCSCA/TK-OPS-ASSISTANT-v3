import type {
  AccountDto,
  AccountReadinessItemDto,
  AccountStatus,
  AccountWizardStep
} from "@/types/runtime/accounts";

export function accountInitial(account: Pick<AccountDto, "name" | "username">): string {
  const source = account.name.trim() || account.username?.trim() || "T";
  return Array.from(source)[0]?.toLocaleUpperCase("zh-CN") ?? "T";
}

export function accountIdentityLabel(account: AccountDto): string {
  return account.username ? `@${account.username}` : "未填写 TikTok 用户名";
}

export function accountStatusLabel(status: AccountStatus): string {
  const labels: Record<AccountStatus, string> = {
    draft: "草稿",
    unbound: "未连接",
    ready: "就绪",
    attention: "需处理",
    archived: "已归档"
  };
  return labels[status];
}

export function accountStatusTone(
  status: AccountStatus
): "neutral" | "success" | "warning" | "danger" {
  if (status === "ready") return "success";
  if (status === "attention") return "danger";
  if (status === "unbound") return "warning";
  return "neutral";
}

export function readinessTone(
  item: AccountReadinessItemDto
): "success" | "warning" | "danger" | "neutral" {
  if (item.status === "ready") return "success";
  if (item.status === "checking") return "warning";
  if (item.status === "blocked" || item.status === "attention") return "danger";
  return "neutral";
}

export function readinessShortLabel(item: AccountReadinessItemDto): string {
  const labels: Record<AccountReadinessItemDto["status"], string> = {
    ready: "就绪",
    attention: "需处理",
    blocked: "受阻",
    missing: "缺失",
    empty: "未配置",
    checking: "检查中"
  };
  return labels[item.status];
}

export function formatAccountDate(value: string | null | undefined): string {
  if (!value) return "尚未使用";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(date);
}

export function wizardStepLabel(step: AccountWizardStep): string {
  const labels: Record<AccountWizardStep, string> = {
    identity: "身份",
    connection: "连接",
    positioning: "定位",
    knowledge: "知识",
    ai_recipe: "AI 配方",
    health: "检查"
  };
  return labels[step];
}

export function inferCompletedWizardSteps(account: AccountDto): AccountWizardStep[] {
  const completed: AccountWizardStep[] = ["identity"];
  if (account.readiness.connection.status === "ready") completed.push("connection");
  if (account.positioningSummary?.trim()) completed.push("positioning");
  if (account.readiness.knowledge.status === "ready") completed.push("knowledge");
  if (account.readiness.ai.status === "ready") completed.push("ai_recipe");
  if (
    account.readiness.checkedAt &&
    account.readiness.connection.status !== "checking" &&
    account.readiness.knowledge.status !== "checking" &&
    account.readiness.ai.status !== "checking"
  ) {
    completed.push("health");
  }
  return completed;
}

