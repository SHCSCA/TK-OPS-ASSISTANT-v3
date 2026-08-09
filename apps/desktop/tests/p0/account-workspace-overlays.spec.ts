import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AccountContextDetailPanel from "@/layouts/account-workspace/AccountContextDetailPanel.vue";
import LegacyRouteMigrationNotice from "@/layouts/account-workspace/LegacyRouteMigrationNotice.vue";
import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";

describe("P0 工作区覆盖层", () => {
  it("账号详情只展示当前 Context 的真实范围摘要", () => {
    const wrapper = mount(AccountContextDetailPanel, {
      attachTo: document.body,
      props: {
        context: workspaceContext(),
        open: true
      }
    });
    const panel = document.querySelector(
      '[data-testid="account-context-detail"]'
    );

    expect(panel?.textContent).toContain("账号 Alpha");
    expect(panel?.textContent).toContain("@alpha_creator");
    expect(panel?.textContent).toContain("账号修订");
    expect(panel?.textContent).toContain("工作区修订");
    expect(panel?.textContent).toContain("2");
    expect(panel?.textContent).toContain("1");
    wrapper.unmount();
  });

  it("旧入口迁移提示可显式关闭", async () => {
    const wrapper = mount(LegacyRouteMigrationNotice, {
      props: {
        message: "旧 AI 剪辑工作台已退出主线。"
      }
    });

    expect(wrapper.get('[data-testid="legacy-route-notice"]').text())
      .toContain("旧 AI 剪辑工作台已退出主线");
    await wrapper.get('button[aria-label="关闭迁移提示"]').trigger("click");

    expect(wrapper.emitted("dismiss")).toHaveLength(1);
  });
});

function workspaceContext(): AccountWorkspaceContextDto {
  const ready = {
    status: "ready" as const,
    label: "已就绪",
    errorCode: null,
    logId: null,
    checkedAt: "2026-07-26T12:00:00Z",
    suggestedAction: null
  };
  return {
    account: {
      id: "account-alpha",
      name: "账号 Alpha",
      username: "alpha_creator",
      platform: "tiktok",
      status: "ready",
      positioningSummary: "面向效率工具用户",
      lastUsedAt: "2026-07-26T12:00:00Z",
      readiness: {
        connection: { ...ready },
        knowledge: { ...ready },
        ai: { ...ready },
        overall: "ready",
        checkedAt: "2026-07-26T12:00:00Z",
        suggestedAction: null
      },
      wizardCompletedAt: "2026-07-26T12:00:00Z",
      revision: 7
    },
    readiness: {
      connection: { ...ready },
      knowledge: { ...ready },
      ai: { ...ready },
      overall: "ready",
      checkedAt: "2026-07-26T12:00:00Z",
      suggestedAction: null
    },
    navigation: {
      lastRoute: "/workspace",
      availableRoutes: ["account_workspace_home"]
    },
    taskSummary: {
      running: 2,
      failed: 1
    },
    workspaceRevision: 11
  };
}
