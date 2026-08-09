import { InvalidAccountIdentifierError } from "./errors";

const STABLE_ACCOUNT_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

export function normalizeAccountId(accountId: string): string {
  const normalized = accountId.trim();
  if (!STABLE_ACCOUNT_ID.test(normalized)) {
    throw new InvalidAccountIdentifierError();
  }
  return normalized;
}

export function normalizeRoute(route: string): string {
  const normalized = route.trim();
  if (!isValidRoute(normalized)) {
    throw new Error("账号最近页面必须是长度不超过 256 的应用内绝对路径。");
  }
  return normalized;
}

export function normalizeRouteMap(
  routes: Record<string, string>
): Record<string, string> {
  const normalized: Record<string, string> = {};
  for (const [accountId, route] of Object.entries(routes)) {
    if (!STABLE_ACCOUNT_ID.test(accountId) || !isValidRoute(route)) {
      continue;
    }
    normalized[accountId] = route;
  }
  return normalized;
}

export function isValidRoute(route: string): boolean {
  return (
    route.length > 0
    && route.length <= 256
    && route.startsWith("/")
    && !route.startsWith("//")
    && !route.includes("://")
  );
}
