import { describe, expect, it } from "vitest";

import { resolveWorkspaceAction } from "@/app/actions";

describe("P0-G 账号动作路由", () => {
  it("只解析当前账号允许的连接动作", () => {
    const result = resolveWorkspaceAction(
      {
        version: 1,
        action: "open_connection",
        accountId: "account-a",
        routeId: "account_management",
        wizardStep: "connection",
        environmentId: "environment-a"
      },
      "account-a"
    );

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.to).toEqual({
      name: "account_management",
      query: {
        account: "account-a",
        action: "continue",
        environment: "environment-a",
        section: "connection",
        source: "workspace-action"
      }
    });
  });

  it("账号不匹配时 fail-closed", () => {
    const result = resolveWorkspaceAction(
      {
        version: 1,
        action: "open_connection",
        accountId: "account-b",
        routeId: "account_management"
      },
      "account-a"
    );

    expect(result).toMatchObject({
      ok: false,
      code: "ACTION_ACCOUNT_MISMATCH",
      fallback: {
        name: "account_management",
        query: { account: "account-a" }
      }
    });
  });

  it("动作与路由不匹配时不接受任意内部跳转", () => {
    const result = resolveWorkspaceAction(
      {
        version: 1,
        action: "open_environment",
        accountId: "account-a",
        routeId: "account_publishing"
      },
      "account-a"
    );

    expect(result).toMatchObject({
      ok: false,
      code: "ACTION_ROUTE_FORBIDDEN"
    });
  });

  it("拒绝许可证页作为 returnTo", () => {
    const result = resolveWorkspaceAction(
      {
        version: 1,
        action: "open_connection",
        accountId: "account-a",
        routeId: "account_management",
        returnTo: { routeId: "setup_license_wizard" }
      },
      "account-a"
    );

    expect(result).toMatchObject({
      ok: false,
      code: "ACTION_ROUTE_FORBIDDEN"
    });
  });
});
