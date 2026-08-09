import { mount, RouterLinkStub } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AccountWorkspaceHomePage from "@/pages/workspace-home/AccountWorkspaceHomePage.vue";
import type {
  AccountReadinessDto,
  AccountWorkspaceContextDto
} from "@/types/runtime/accounts";

describe("P0 账号工作台首页", () => {
  it("没有账号时显示中性依赖态且不伪造任务数字", () => {
    const wrapper = mountPage();

    expect(wrapper.get('[data-state="dependency_blocked"]').text()).toContain(
      "请选择账号工作区"
    );
    expect(wrapper.find('[data-testid="workspace-running-count"]').exists()).toBe(false);
  });

  it("账号 Context 尚未到达或属于旧账号时只显示加载态", () => {
    const wrapper = mountPage({
      accountId: "account-2",
      workspaceContext: workspaceFixture()
    });

    expect(wrapper.get('[data-state="loading"]').text()).toContain(
      "不会展示其他账号的数据"
    );
    expect(wrapper.text()).not.toContain("账号一");
  });

  it("只展示当前账号的真实就绪状态和任务汇总", () => {
    const wrapper = mountPage({
      accountId: "account-1",
      workspaceContext: workspaceFixture()
    });

    expect(wrapper.text()).toContain("账号一");
    expect(wrapper.text()).toContain("@creator_one");
    expect(wrapper.text()).toContain("服务职场新人的效率账号");
    expect(wrapper.text()).toContain("账号连接");
    expect(wrapper.text()).toContain("知识库");
    expect(wrapper.text()).toContain("AI 配方");
    expect(wrapper.get('[data-testid="workspace-running-count"]').text()).toBe("2");
    expect(wrapper.get('[data-testid="workspace-failed-count"]').text()).toBe("1");
  });

  it("优先采用 Runtime 返回的下一步入口", () => {
    const context = workspaceFixture();
    context.readiness.suggestedAction = {
      actionKey: "open_knowledge",
      label: "补充知识来源",
      routeId: "account_strategy_knowledge",
      section: "sources",
      taskId: null
    };

    const wrapper = mountPage({
      accountId: "account-1",
      workspaceContext: context
    });
    const action = wrapper.getComponent(RouterLinkStub);

    expect(action.text()).toContain("补充知识来源");
    expect(action.props("to")).toEqual({
      name: "account_strategy_knowledge",
      query: {
        account: "account-1",
        section: "sources",
        source: "workspace-action"
      }
    });
  });

  it("拒绝 Runtime 注入的越权路由并显示可见反馈", () => {
    const context = workspaceFixture();
    context.readiness.suggestedAction = {
      actionKey: "open_connection",
      label: "打开外部页面",
      routeId: "setup_license_wizard",
      section: null,
      taskId: null
    };

    const wrapper = mountPage({
      accountId: "account-1",
      workspaceContext: context
    });

    expect(wrapper.get('[data-testid="workspace-action-feedback"]').text()).toContain(
      "目标不在允许范围"
    );
    expect(wrapper.getComponent(RouterLinkStub).props("to")).toEqual({
      name: "account_management",
      query: { account: "account-1" }
    });
  });
});

function mountPage(props?: {
  accountId?: string | null;
  workspaceContext?: AccountWorkspaceContextDto | null;
}) {
  return mount(AccountWorkspaceHomePage, {
    props,
    global: {
      components: { RouterLink: RouterLinkStub }
    }
  });
}

function workspaceFixture(): AccountWorkspaceContextDto {
  const readiness = readinessFixture();
  return {
    account: {
      id: "account-1",
      name: "账号一",
      username: "creator_one",
      platform: "tiktok",
      status: "attention",
      positioningSummary: "服务职场新人的效率账号",
      lastUsedAt: "2026-07-26T10:00:00Z",
      readiness,
      wizardCompletedAt: null,
      revision: 4
    },
    readiness,
    navigation: {
      lastRoute: "/workspace",
      availableRoutes: [
        "account_workspace_home",
        "account_strategy_knowledge",
        "account_script_topic"
      ]
    },
    taskSummary: {
      running: 2,
      failed: 1
    },
    workspaceRevision: 8
  };
}

function readinessFixture(): AccountReadinessDto {
  return {
    connection: {
      status: "ready",
      label: "浏览器连接正常",
      errorCode: null,
      logId: null,
      checkedAt: "2026-07-26T10:00:00Z",
      suggestedAction: null
    },
    knowledge: {
      status: "empty",
      label: "尚未添加知识来源",
      errorCode: null,
      logId: null,
      checkedAt: "2026-07-26T10:00:00Z",
      suggestedAction: null
    },
    ai: {
      status: "checking",
      label: "正在检查 AI 配方",
      errorCode: null,
      logId: null,
      checkedAt: "2026-07-26T10:00:00Z",
      suggestedAction: null
    },
    overall: "attention",
    checkedAt: "2026-07-26T10:00:00Z",
    suggestedAction: null
  };
}
