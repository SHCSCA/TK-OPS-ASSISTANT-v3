import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import AccountCreationWizard from "@/modules/accounts/components/AccountCreationWizard.vue";
import AccountListTable from "@/modules/accounts/components/AccountListTable.vue";
import type { AccountDto } from "@/types/runtime/accounts";

const accountApi = vi.hoisted(() => ({
  archiveAccount: vi.fn(),
  bindAccountConnection: vi.fn(),
  completeAccountWizard: vi.fn(),
  copyAccountConfig: vi.fn(),
  createAccount: vi.fn(),
  getAccount: vi.fn(),
  getAccountConnection: vi.fn(),
  listAccountConnectionCandidates: vi.fn(),
  listAccounts: vi.fn(),
  restoreAccount: vi.fn(),
  startAccountHealthChecks: vi.fn()
}));
const environmentApi = vi.hoisted(() => ({
  listExecutionEnvironments: vi.fn()
}));

vi.mock("@/app/runtime-client/accounts", () => accountApi);
vi.mock("@/app/runtime-client/execution-environments", () => environmentApi);

describe("P0 账号管理 UI", () => {
  it("使用固定列展示真实身份、定位、三项就绪和推荐动作", async () => {
    const account = accountFixture({
      positioningSummary: "已配置 2 个内容支柱",
      lastUsedAt: "2026-07-26T10:00:00Z"
    });
    const wrapper = mount(AccountListTable, {
      props: {
        accounts: [account],
        collectionState: "ready",
        selectedAccountId: null
      }
    });

    const headings = wrapper.findAll("th").map((item) => item.text());
    expect(headings).toEqual([
      "身份",
      "定位摘要",
      "三项就绪",
      "生命周期",
      "最近使用",
      "推荐动作"
    ]);
    expect(wrapper.text()).toContain("@efficiency.lab");
    expect(wrapper.text()).toContain("已配置 2 个内容支柱");
  });

  it("无账号和过滤无结果使用不同中性空态", async () => {
    const wrapper = mount(AccountListTable, {
      props: {
        accounts: [],
        collectionState: "empty",
        selectedAccountId: null
      }
    });
    expect(wrapper.text()).toContain("还没有 TikTok 账号");
    expect(wrapper.text()).toContain("添加账号");

    await wrapper.setProps({ collectionState: "filtered-empty" });
    expect(wrapper.text()).toContain("没有匹配账号");
    expect(wrapper.text()).toContain("清除筛选");
  });

  it("六步向导在没有真实连接候选时保持阻塞，AI 步骤不假完成", async () => {
    const draft = accountFixture();
    accountApi.listAccountConnectionCandidates.mockResolvedValue({
      data: { items: [] },
      meta: null,
      operationId: null,
      requestId: "request-1",
      status: 200
    });
    environmentApi.listExecutionEnvironments.mockResolvedValue({
      data: { items: [] },
      meta: null,
      operationId: null,
      requestId: "request-environments-1",
      status: 200
    });
    accountApi.getAccountConnection.mockResolvedValue({
      data: {
        accountId: draft.id,
        authStatus: "required",
        healthStatus: "unknown",
        deviceWorkspace: null,
        browserInstance: null,
        executionBinding: null,
        lastCheck: null,
        revision: draft.revision
      }
    });
    const wrapper = mount(AccountCreationWizard, {
      global: { plugins: [createPinia()] },
      props: { initialAccount: draft, open: false }
    });

    await wrapper.setProps({ open: true });
    await flushPromises();

    expect(wrapper.findAll(".account-wizard__steps li")).toHaveLength(6);
    expect(wrapper.text()).toContain("还没有执行环境");
    expect(wrapper.text()).toContain("新建执行环境");
    expect(accountApi.completeAccountWizard).not.toHaveBeenCalled();
  });

  it("AI readiness 未就绪时停在账号级 AI 配方步骤", async () => {
    const readyItem = {
      status: "ready" as const,
      label: "已就绪",
      errorCode: null,
      logId: null,
      checkedAt: "2026-07-26T10:00:00Z",
      suggestedAction: null
    };
    const draft = accountFixture({
      positioningSummary: "已配置 2 个内容支柱",
      readiness: {
        connection: { ...readyItem },
        knowledge: { ...readyItem },
        ai: {
          ...readyItem,
          status: "blocked",
          label: "等待 AI 配方"
        },
        overall: "blocked",
        checkedAt: null,
        suggestedAction: null
      }
    });
    const wrapper = mount(AccountCreationWizard, {
      global: {
        plugins: [createPinia()],
        stubs: {
          AccountAIRecipePanel: {
            template: '<section data-testid="account-ai-recipe-step">账号级 AI 配方待完善</section>'
          }
        }
      },
      props: { initialAccount: draft, open: true }
    });
    await flushPromises();

    expect(wrapper.get(".account-wizard__steps li.is-active").text())
      .toContain("AI 配方");
    expect(wrapper.get('[data-testid="account-ai-recipe-step"]').text())
      .toBe("账号级 AI 配方待完善");
    expect(accountApi.completeAccountWizard).not.toHaveBeenCalled();
  });
});

function accountFixture(overrides: Partial<AccountDto> = {}): AccountDto {
  const missing = {
    status: "missing" as const,
    label: "未配置",
    errorCode: null,
    logId: null,
    checkedAt: null,
    suggestedAction: null
  };
  return {
    id: "account-1",
    name: "效率观察",
    username: "efficiency.lab",
    platform: "tiktok",
    status: "draft",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...missing },
      knowledge: { ...missing },
      ai: { ...missing },
      overall: "blocked",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 1,
    ...overrides
  };
}
