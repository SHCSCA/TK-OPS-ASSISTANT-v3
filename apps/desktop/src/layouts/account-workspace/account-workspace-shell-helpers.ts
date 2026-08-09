import { p0RouteManifest } from "@/app/router";
import type { AccountDto } from "@/types/runtime/accounts";

import type {
  AccountSwitcherOption,
  AccountWorkspaceNavItem
} from "./account-workspace-types";

export function createNavigationItems(
  accountScoped: boolean
): AccountWorkspaceNavItem[] {
  return p0RouteManifest
    .filter(
      (item) =>
        item.scope === (accountScoped ? "account" : "system")
        && item.navOrder !== null
        && item.navSection !== "hidden"
    )
    .sort((left, right) => (
      (left.navOrder ?? Number.MAX_SAFE_INTEGER)
      - (right.navOrder ?? Number.MAX_SAFE_INTEGER)
    ))
    .map(({ id, icon, path, title }) => ({ id, icon, path, title }));
}

export function mergeCurrentAccount(
  accounts: AccountDto[],
  current: AccountDto | null
): AccountDto[] {
  if (!current) return accounts;
  const index = accounts.findIndex((account) => account.id === current.id);
  if (index < 0) return [current, ...accounts];
  return accounts.map((account) =>
    account.id === current.id ? current : account
  );
}

export function toSwitcherOption(
  account: AccountDto
): AccountSwitcherOption {
  return {
    id: account.id,
    name: account.name,
    username: account.username,
    status: account.status,
    positioningSummary: account.positioningSummary
  };
}

export function readQueryAccount(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

export function readCompactWindow(): boolean {
  return typeof window !== "undefined" && window.innerWidth < 1280;
}

export function switchStatusMessage(status: string): string {
  switch (status) {
    case "guarding":
      return "正在确认未保存内容…";
    case "preparing":
      return "正在预加载目标账号工作区…";
    case "committing":
      return "正在切换账号上下文…";
    case "refreshing":
      return "正在同步账号最新状态…";
    default:
      return "正在准备账号工作区…";
  }
}
