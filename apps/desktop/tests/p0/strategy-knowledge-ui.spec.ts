import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { routeLocationKey, routerKey } from "vue-router";

import { RuntimeError } from "@/app/runtime-client/core";
import { accountUnsavedGuardRegistrarKey } from "@/modules/accounts/account-guard-port";
import KnowledgeSourcesPanel from "@/modules/knowledge/KnowledgeSourcesPanel.vue";
import {
  createAccountKnowledgeCache,
  useAccountKnowledgeStore,
  type AccountUnsavedGuardRegister
} from "@/modules/knowledge";
import AccountStrategyKnowledgePage from "@/pages/strategy-knowledge/AccountStrategyKnowledgePage.vue";

const runtime = vi.hoisted(() => ({
  getAccountPositioning: vi.fn(),
  getAccountPositioningVersion: vi.fn(),
  getAccountKnowledge: vi.fn(),
  listAccountKnowledgeSources: vi.fn(),
  getAccountBrandKit: vi.fn(),
  getAccountTask: vi.fn(),
  createAccountPositioningVersion: vi.fn(),
  activateAccountPositioningVersion: vi.fn(),
  updateAccountKnowledgeRules: vi.fn(),
  createAccountKnowledgeSource: vi.fn(),
  removeAccountKnowledgeSource: vi.fn(),
  startAccountKnowledgeIndex: vi.fn()
}));

vi.mock("@/app/runtime-client/account-knowledge", () => ({
  getAccountPositioning: runtime.getAccountPositioning,
  getAccountPositioningVersion: runtime.getAccountPositioningVersion,
  getAccountKnowledge: runtime.getAccountKnowledge,
  listAccountKnowledgeSources: runtime.listAccountKnowledgeSources,
  getAccountBrandKit: runtime.getAccountBrandKit,
  createAccountPositioningVersion: runtime.createAccountPositioningVersion,
  activateAccountPositioningVersion: runtime.activateAccountPositioningVersion,
  updateAccountKnowledgeRules: runtime.updateAccountKnowledgeRules,
  createAccountKnowledgeSource: runtime.createAccountKnowledgeSource,
  removeAccountKnowledgeSource: runtime.removeAccountKnowledgeSource,
  startAccountKnowledgeIndex: runtime.startAccountKnowledgeIndex
}));

vi.mock("@/app/runtime-client/tasks", () => ({
  getAccountTask: runtime.getAccountTask
}));

describe("P0 定位与知识页面", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockEmptyAccount();
  });

  it("未提供当前账号时呈现统一依赖阻塞态且不请求数据", () => {
    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: { plugins: [createPinia()] }
    });

    expect(wrapper.get('[data-state="dependency_blocked"]').text()).toContain(
      "请先选择账号"
    );
    expect(runtime.getAccountPositioning).not.toHaveBeenCalled();
  });

  it("首次使用展示真实空态，并明确只接受受控文件引用", async () => {
    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: { plugins: [createPinia()] },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    expect(wrapper.get('[data-state="first_use"]').text()).toContain(
      "从账号定位开始"
    );
    expect(wrapper.get('[data-testid="brand-kit-panel"]').text()).toContain(
      "不会猜测品牌颜色"
    );
    expect(wrapper.get('[data-state="controlled_file_ready"]').text()).toContain(
      "只接收 fileRef"
    );
    expect(wrapper.text()).not.toContain("C:\\");
    expect(wrapper.text()).not.toContain("1,234");
  });

  it("正常态展示真实激活版本与来源状态", async () => {
    runtime.getAccountPositioning.mockResolvedValue(result({
      accountId: "account-1",
      activeVersion: 2,
      versions: [{
        version: 2,
        status: "active",
        summary: "已配置 2 个内容支柱",
        createdAt: "2026-07-26T10:00:00Z"
      }],
      revision: 4
    }));
    runtime.getAccountKnowledge.mockResolvedValue(result({
      accountId: "account-1",
      rules: {
        inclusionRules: { language: "zh-CN" },
        exclusionRules: {},
        citationPolicy: {}
      },
      rulesVersion: 1,
      sourceCounts: { ready: 1 },
      latestSnapshotId: null,
      readiness: {},
      revision: 4
    }));
    runtime.listAccountKnowledgeSources.mockResolvedValue(result({
      items: [sourceFixture()],
      totalKnown: 1
    }));
    runtime.getAccountPositioningVersion.mockResolvedValue(
      result(positioningVersionFixture({
        id: "positioning-2",
        version: 2
      }))
    );

    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: { plugins: [createPinia()] },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    expect(wrapper.attributes("data-state")).toBe("ready");
    expect(wrapper.text()).toContain("当前定位");
    expect(wrapper.text()).toContain("v2 使用中");
    expect(wrapper.text()).toContain("#直接");
    expect(runtime.getAccountPositioningVersion).toHaveBeenCalledWith(
      "account-1",
      2,
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(wrapper.text()).toContain("公开文档");
    expect(wrapper.text()).toContain("可用");
  });

  it("从账号向导进入时返回同一账号的继续入口", async () => {
    const push = vi.fn().mockResolvedValue(undefined);
    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: {
        plugins: [createPinia()],
        provide: {
          [routeLocationKey as symbol]: {
            query: { from: "account-wizard" }
          },
          [routerKey as symbol]: { push }
        }
      },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    await wrapper.get('[data-testid="return-account-wizard"]').trigger("click");
    expect(push).toHaveBeenCalledWith({
      path: "/settings/accounts",
      query: {
        action: "continue",
        account: "account-1"
      }
    });
  });

  it("定位草稿通过壳层注入接入未保存守卫并支持放弃", async () => {
    const holder: {
      guard: Parameters<AccountUnsavedGuardRegister>[0] | null;
    } = { guard: null };
    const register: AccountUnsavedGuardRegister = (candidate) => {
      holder.guard = candidate;
      return () => {
        holder.guard = null;
      };
    };
    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: {
        plugins: [createPinia()],
        provide: {
          [accountUnsavedGuardRegistrarKey as symbol]: { register }
        }
      },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    await wrapper.get(".sk-first-use button").trigger("click");
    await wrapper.get('[data-testid="positioning-editor"] input').setValue(
      "独立开发者"
    );

    expect(holder.guard?.isDirty()).toBe(true);
    await holder.guard?.discard();
    expect(holder.guard?.isDirty()).toBe(false);
  });

  it("可以查看定位详情并基于历史版本预填新草稿", async () => {
    const originalPositioning = {
      accountId: "account-1",
      activeVersion: 1,
      versions: [{
        version: 1,
        status: "active",
        summary: "面向独立开发者 · 产品拆解 / 增长实验",
        createdAt: "2026-08-02T10:00:00Z"
      }],
      revision: 4
    };
    runtime.getAccountPositioning
      .mockResolvedValueOnce(result(originalPositioning))
      .mockResolvedValueOnce(result({
        ...originalPositioning,
        versions: [
          {
            version: 2,
            status: "draft",
            summary: "面向独立开发者与小团队 · 产品拆解 / 增长实验",
            createdAt: "2026-08-02T12:00:00Z"
          },
          ...originalPositioning.versions
        ],
        revision: 5
      }));
    runtime.getAccountPositioningVersion.mockResolvedValue(
      result(positioningVersionFixture())
    );
    runtime.createAccountPositioningVersion.mockResolvedValue(
      result(positioningVersionFixture({
        id: "positioning-2",
        version: 2,
        status: "draft",
        audience: { description: "准备出海的独立开发者与小团队" },
        summary: "面向独立开发者与小团队 · 产品拆解 / 增长实验",
        activatedAt: null,
        revision: 1
      }))
    );
    const pinia = createPinia();
    const wrapper = mount(AccountStrategyKnowledgePage, {
      attachTo: document.body,
      global: { plugins: [pinia] },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    const detailButton = wrapper
      .findAll("button")
      .find((button) => button.text() === "查看详情");
    expect(detailButton).toBeDefined();
    await detailButton!.trigger("click");
    await flushPromises();

    const detailPanel = document.body.querySelector<HTMLElement>(
      '[data-testid="positioning-detail-panel"]'
    );
    expect(detailPanel?.textContent).toContain("准备出海的独立开发者");
    expect(detailPanel?.textContent).toContain("产品拆解");
    expect(detailPanel?.textContent).toContain("未经验证的收益承诺");
    const editButton = Array.from(
      detailPanel!.querySelectorAll<HTMLButtonElement>("button")
    ).find((button) => button.textContent?.trim() === "基于此版本修改");
    expect(editButton).toBeDefined();
    editButton!.click();
    await flushPromises();

    const editor = wrapper.get('[data-testid="positioning-editor"]');
    expect(editor.text()).toContain("基于 v1 修改");
    expect(editor.get("input").element.value).toBe(
      "准备出海的独立开发者"
    );
    expect(
      useAccountKnowledgeStore(pinia).cache("account-1").positioningDirty
    ).toBe(false);
    await editor.get("input").setValue("准备出海的独立开发者与小团队");
    expect(
      useAccountKnowledgeStore(pinia).cache("account-1").positioningDirty
    ).toBe(true);
    await editor.trigger("submit");
    await flushPromises();

    expect(runtime.createAccountPositioningVersion).toHaveBeenCalledWith(
      "account-1",
      expect.objectContaining({
        audience: { description: "准备出海的独立开发者与小团队" },
        contentPillars: ["产品拆解", "增长实验"],
        tone: { description: "直接、克制、有证据" },
        prohibitedTopics: ["未经验证的收益承诺"],
        publishingConstraints: { description: "结论必须附带来源" }
      }),
      expect.objectContaining({
        expectedRevision: 4,
        idempotencyKey: expect.stringContaining(
          "positioning-create:account-1:"
        )
      })
    );
    expect(wrapper.find('[data-testid="positioning-editor"]').exists()).toBe(
      false
    );
    expect(
      useAccountKnowledgeStore(pinia).cache("account-1").positioningDetailVersion
    ).toBe(2);
    wrapper.unmount();
  });

  it("定位详情失败只影响详情面板并保留局部重试入口", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    runtime.getAccountPositioning.mockResolvedValue(result({
      accountId: "account-1",
      activeVersion: null,
      versions: [{
        version: 1,
        status: "draft",
        summary: "面向独立开发者 · 产品拆解",
        createdAt: "2026-08-02T10:00:00Z"
      }],
      revision: 4
    }));
    runtime.getAccountPositioningVersion.mockRejectedValue(
      new RuntimeError("定位版本暂时无法读取。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-detail-1",
        status: 503
      })
    );
    const wrapper = mount(AccountStrategyKnowledgePage, {
      attachTo: document.body,
      global: { plugins: [createPinia()] },
      props: { accountId: "account-1" }
    });
    await flushPromises();

    const detailButton = wrapper
      .findAll("button")
      .find((button) => button.text() === "查看详情");
    await detailButton!.trigger("click");
    await flushPromises();

    expect(wrapper.attributes("data-state")).not.toBe("error");
    const detailPanel = document.body.querySelector<HTMLElement>(
      '[data-testid="positioning-detail-panel"]'
    );
    expect(detailPanel?.textContent).toContain("定位版本暂时无法读取");
    expect(detailPanel?.textContent).toContain("日志 log-detail-1");
    expect(detailPanel?.textContent).toContain("重新加载");
    expect(wrapper.text()).toContain("知识来源");
    wrapper.unmount();
    errorSpy.mockRestore();
  });

  it("连续选择定位版本时忽略迟到响应", async () => {
    const versionOne = deferred<ReturnType<typeof result>>();
    const versionTwo = deferred<ReturnType<typeof result>>();
    runtime.getAccountPositioningVersion.mockImplementation(
      (_accountId: string, version: number) =>
        version === 1 ? versionOne.promise : versionTwo.promise
    );
    const pinia = createPinia();
    const store = useAccountKnowledgeStore(pinia);

    const first = store.openPositioningDetail("account-1", 1);
    const second = store.openPositioningDetail("account-1", 2);
    versionTwo.resolve(result(positioningVersionFixture({
      id: "positioning-2",
      version: 2
    })));
    await second;
    versionOne.resolve(result(positioningVersionFixture()));
    await first;

    const cache = store.cache("account-1");
    expect(cache.positioningDetailVersion).toBe(2);
    expect(cache.positioningDetail?.version).toBe(2);
    expect(cache.positioningDetailState).toBe("ready");
  });

  it("来源列表区分过滤空态与任务等待态", async () => {
    const cache = createAccountKnowledgeCache("account-1");
    cache.sourceState = "filtered_empty";
    const wrapper = mount(KnowledgeSourcesPanel, { props: { cache } });
    expect(wrapper.get('[data-state="filtered_empty"]').text()).toContain(
      "当前筛选下没有来源"
    );

    cache.sourceState = "waiting";
    cache.indexTaskId = "task-1";
    await wrapper.setProps({ cache: { ...cache } });
    expect(wrapper.get('[data-state="waiting"]').text()).toContain("task-1");
  });

  it("Runtime 错误展示中文反馈和日志引用", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    runtime.getAccountPositioning.mockRejectedValue(
      new RuntimeError("定位服务暂不可用。", {
        errorCode: "RUNTIME_NOT_READY",
        logId: "log-1",
        status: 503
      })
    );
    const pinia = createPinia();
    const wrapper = mount(AccountStrategyKnowledgePage, {
      global: { plugins: [pinia] },
      props: { accountId: "account-error" }
    });
    await flushPromises();
    await vi.waitFor(() => {
      expect(runtime.getAccountPositioning).toHaveBeenCalled();
      expect(
        useAccountKnowledgeStore(pinia).cache("account-error").pageState
      ).toBe("error");
    });
    await nextTick();

    const state = wrapper.get('.sk-page-state[data-state="error"]');
    expect(state.text()).toContain("定位服务暂不可用");
    expect(state.text()).toContain("日志 log-1");
    expect(state.text()).toContain("重试");
  });
});

function mockEmptyAccount(): void {
  runtime.getAccountPositioning.mockResolvedValue(result({
    accountId: "account-1",
    activeVersion: null,
    versions: [],
    revision: 1
  }));
  runtime.getAccountPositioningVersion.mockResolvedValue(
    result(positioningVersionFixture())
  );
  runtime.getAccountKnowledge.mockResolvedValue(result({
    accountId: "account-1",
    rules: {
      inclusionRules: {},
      exclusionRules: {},
      citationPolicy: {}
    },
    rulesVersion: 0,
    sourceCounts: {},
    latestSnapshotId: null,
    readiness: {},
    revision: 1
  }));
  runtime.listAccountKnowledgeSources.mockResolvedValue(result({
    items: [],
    totalKnown: 0
  }));
  runtime.getAccountBrandKit.mockResolvedValue(result({
    accountId: "account-1",
    activeVersion: null,
    versions: [],
    active: null,
    revision: 1
  }));
}

function result<T>(data: T) {
  return {
    data,
    meta: null,
    operationId: null,
    requestId: "request-1",
    status: 200
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function sourceFixture() {
  return {
    id: "source-1",
    accountId: "account-1",
    kind: "reference",
    sourceMode: "url",
    title: "公开文档",
    status: "ready",
    controlledRef: null,
    sourceUrl: "https://example.com/guide",
    contentHash: "a".repeat(64),
    indexedAt: "2026-07-26T10:00:00Z",
    removedAt: null,
    errorCode: null,
    logId: null,
    revision: 1
  };
}

function positioningVersionFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "positioning-1",
    accountId: "account-1",
    version: 1,
    status: "active",
    summary: "面向准备出海的独立开发者 · 产品拆解 / 增长实验",
    createdAt: "2026-08-02T10:00:00Z",
    audience: { description: "准备出海的独立开发者" },
    contentPillars: ["产品拆解", "增长实验"],
    tone: { description: "直接、克制、有证据" },
    prohibitedTopics: ["未经验证的收益承诺"],
    publishingConstraints: { description: "结论必须附带来源" },
    contentHash: "a".repeat(64),
    activatedAt: "2026-08-02T11:00:00Z",
    revision: 2,
    ...overrides
  };
}
