import {
  defineComponent,
  inject,
  onBeforeUnmount,
  type Component,
  type PropType
} from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import {
  createMemoryHistory,
  createRouter
} from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AccountDto,
  AccountWorkspaceContextDto
} from "@/types/runtime/accounts";

const shellMocks = vi.hoisted(() => {
  const unregisterGuard = vi.fn();
  const directory = {
    accounts: [] as AccountDto[],
    status: "empty" as "empty" | "error" | "ready",
    error: null as {
      message: string;
      logId: string | null;
      requestId: string | null;
      retryable: boolean;
    } | null,
    load: vi.fn().mockResolvedValue(undefined),
    merge: vi.fn()
  };
  const contextState = {
    currentAccountId: null as string | null,
    currentAccount: null as AccountWorkspaceContextDto | null,
    switchStatus: "idle",
    error: null as {
      message: string;
      logId: string | null;
      retryable: boolean;
    } | null
  };
  const socketState = {
    status: "idle",
    error: null as { message: string } | null
  };
  const unsavedDecision = {
    state: {
      pending: null as {
        id: number;
        prompt: {
          reason: "account-switch";
          sourceAccountId: string;
          targetAccountId: string;
          guards: Array<{ id: string; label: string }>;
          signal: AbortSignal;
        };
      } | null
    },
    resolved: null as "save" | "discard" | "cancel" | null,
    resolve: vi.fn()
  };
  unsavedDecision.resolve.mockImplementation(function resolve(
    this: typeof unsavedDecision,
    decision: "save" | "discard" | "cancel"
  ) {
    this.resolved = decision;
    this.state.pending = null;
  });
  const application = {
    navigationState: {
      error: null as {
        message: string;
        logId: string | null;
      } | null
    },
    context: {
      state: contextState,
      clearCurrentAccount: vi.fn().mockResolvedValue(undefined),
      switchAccount: vi.fn().mockResolvedValue({ status: "unchanged" }),
      retryLastFailure: vi.fn().mockResolvedValue(null)
    },
    uiConfig: {
      state: {
        theme: "system" as "system" | "light" | "dark",
        error: null as {
          message: string;
          logId: string | null;
          retryable: boolean;
        } | null
      },
      load: vi.fn().mockResolvedValue(undefined),
      toggleTheme: vi.fn().mockResolvedValue(undefined)
    },
    eventSocket: {
      state: socketState,
      onEvent: vi.fn(() => vi.fn()),
      retryCurrent: vi.fn().mockResolvedValue(undefined)
    },
    unsavedDecision,
    unsavedGuards: {
      register: vi.fn(() => unregisterGuard)
    },
    initialize: vi.fn().mockResolvedValue(undefined)
  };
  return {
    application,
    contextState,
    directory,
    socketState,
    unregisterGuard
  };
});

vi.mock("@/app/account-context", () => ({
  accountContextApplication: shellMocks.application,
  consoleAccountContextLogger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  },
  useAccountDirectoryStore: () => shellMocks.directory
}));

import { accountUnsavedGuardRegistrarKey } from "@/modules/accounts/account-guard-port";
import AccountWorkspaceLayout from "@/layouts/account-workspace/AccountWorkspaceLayout.vue";

const WorkspaceProbe = defineComponent({
  props: {
    accountId: {
      type: String as PropType<string | null>,
      default: null
    },
    workspaceContext: {
      type: Object as PropType<AccountWorkspaceContextDto | null>,
      default: null
    }
  },
  template: `
    <section
      data-testid="workspace-probe"
      :data-account-id="accountId ?? 'hidden'"
    >
      {{ workspaceContext?.account.name ?? "snapshot-hidden" }}
    </section>
  `
});

const GuardProbe = defineComponent({
  setup() {
    const registrar = inject(accountUnsavedGuardRegistrarKey);
    if (!registrar) {
      throw new Error("账号未保存守卫端口未注入。");
    }
    const unregister = registrar.register({
      id: "script-draft",
      label: "脚本草稿",
      isDirty: () => true,
      save: async () => undefined,
      discard: () => undefined
    });
    onBeforeUnmount(unregister);
    return {};
  },
  template: '<section data-testid="guard-probe">守卫已注册</section>'
});

describe("P0 账号工作区壳层", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    shellMocks.directory.accounts = [];
    shellMocks.directory.status = "empty";
    shellMocks.directory.error = null;
    shellMocks.contextState.currentAccountId = null;
    shellMocks.contextState.currentAccount = null;
    shellMocks.contextState.switchStatus = "idle";
    shellMocks.contextState.error = null;
    shellMocks.socketState.status = "idle";
    shellMocks.socketState.error = null;
    shellMocks.application.navigationState.error = null;
    shellMocks.application.uiConfig.state.theme = "system";
    shellMocks.application.uiConfig.state.error = null;
    shellMocks.application.unsavedDecision.state.pending = null;
    shellMocks.application.unsavedDecision.resolved = null;
    shellMocks.application.unsavedGuards.register.mockReturnValue(
      shellMocks.unregisterGuard
    );
  });

  it("没有账号时保留真实账号级路由并展示中性空态", async () => {
    const { wrapper, router } = await mountShell(WorkspaceProbe);

    expect(router.currentRoute.value.path).toBe("/workspace");
    expect(wrapper.get(".account-workspace-empty").text()).toContain(
      "选择一个账号工作区"
    );
    expect(wrapper.text()).toContain(
      "定位、知识、内容与任务按 TikTok 账号独立保存"
    );
    expect(wrapper.find('[data-testid="workspace-probe"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("切换期间不把旧账号快照传给目标路由页面", async () => {
    shellMocks.contextState.currentAccountId = "account-old";
    shellMocks.contextState.currentAccount = workspaceContext("account-old");
    shellMocks.contextState.switchStatus = "preparing";

    const { wrapper } = await mountShell(WorkspaceProbe);
    const probe = wrapper.get('[data-testid="workspace-probe"]');

    expect(probe.attributes("data-account-id")).toBe("hidden");
    expect(probe.text()).toBe("snapshot-hidden");
    expect(wrapper.get(".account-workspace-switch-mask").text()).toContain(
      "旧账号内容已暂时隐藏"
    );
    wrapper.unmount();
  });

  it("未保存守卫决策期间保留当前账号页面，避免守卫被提前注销", async () => {
    shellMocks.contextState.currentAccountId = "account-old";
    shellMocks.contextState.currentAccount = workspaceContext("account-old");
    shellMocks.contextState.switchStatus = "guarding";

    const { wrapper } = await mountShell(GuardProbe);

    expect(wrapper.get('[data-testid="guard-probe"]').exists()).toBe(true);
    expect(shellMocks.application.unsavedGuards.register).toHaveBeenCalledWith(
      expect.objectContaining({ id: "script-draft" })
    );
    expect(wrapper.find(".account-workspace-switch-mask").exists()).toBe(false);
    wrapper.unmount();
  });

  it("账号目录错误在状态栏可见并提供真实重试动作", async () => {
    shellMocks.directory.status = "error";
    shellMocks.directory.error = {
      message: "账号目录加载失败，请稍后重试。",
      logId: "log-directory",
      requestId: "request-directory",
      retryable: true
    };

    const { wrapper } = await mountShell(WorkspaceProbe);
    const feedback = wrapper.get(".account-status-feedback");

    expect(feedback.text()).toContain("账号目录加载失败，请稍后重试。");
    expect(feedback.text()).toContain("重试");
    await feedback
      .findAll("button")
      .find((button) => button.text() === "重试")
      ?.trigger("click");
    await flushPromises();

    expect(shellMocks.directory.load).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it.each([
    ["取消", "cancel"],
    ["放弃并继续", "discard"],
    ["保存并继续", "save"]
  ] as const)("未保存弹窗点击%s会通过控制器实例提交%s", async (
    label,
    decision
  ) => {
    shellMocks.application.unsavedDecision.state.pending = {
      id: 1,
      prompt: {
        reason: "account-switch",
        sourceAccountId: "account-old",
        targetAccountId: "account-new",
        guards: [{ id: "positioning", label: "定位与知识" }],
        signal: new AbortController().signal
      }
    };
    const { wrapper } = await mountShell(WorkspaceProbe);

    const button = Array.from(
      document.body.querySelectorAll<HTMLButtonElement>(
        ".account-unsaved-dialog__actions button"
      )
    ).find((candidate) => candidate.textContent?.trim() === label);
    expect(button).toBeDefined();
    button!.click();
    await flushPromises();

    expect(shellMocks.application.unsavedDecision.resolved).toBe(decision);
    wrapper.unmount();
  });

  it("未保存弹窗提交后立即锁定操作，防止重复决策", async () => {
    shellMocks.application.unsavedDecision.state.pending = {
      id: 2,
      prompt: {
        reason: "account-switch",
        sourceAccountId: "account-old",
        targetAccountId: "account-new",
        guards: [{ id: "positioning", label: "定位与知识" }],
        signal: new AbortController().signal
      }
    };
    shellMocks.application.unsavedDecision.resolve.mockImplementationOnce(
      function resolveWithoutClosing(
        this: typeof shellMocks.application.unsavedDecision,
        decision: "save" | "discard" | "cancel"
      ) {
        this.resolved = decision;
      }
    );
    const { wrapper } = await mountShell(WorkspaceProbe);

    const saveButton = Array.from(
      document.body.querySelectorAll<HTMLButtonElement>(
        ".account-unsaved-dialog__actions button"
      )
    ).find((candidate) => candidate.textContent?.trim() === "保存并继续");
    expect(saveButton).toBeDefined();
    saveButton!.click();
    saveButton!.click();
    document.querySelector<HTMLElement>(".account-unsaved-dialog")
      ?.dispatchEvent(new KeyboardEvent("keydown", {
        bubbles: true,
        key: "Escape"
      }));
    document.querySelector<HTMLElement>(".account-unsaved-backdrop")
      ?.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    await flushPromises();

    expect(shellMocks.application.unsavedDecision.resolve).toHaveBeenCalledOnce();
    expect(
      Array.from(
        document.body.querySelectorAll<HTMLButtonElement>(
          ".account-unsaved-dialog__actions button"
        )
      ).every((button) => button.disabled)
    ).toBe(true);
    wrapper.unmount();
  });

  it("账号事件离线时提示 HTTP 降级状态并允许重连", async () => {
    shellMocks.socketState.status = "offline";
    shellMocks.socketState.error = {
      message: "账号事件连接已断开，页面将使用 HTTP 状态继续工作。"
    };

    const { wrapper } = await mountShell(WorkspaceProbe);
    const feedback = wrapper.get(".account-status-feedback");

    expect(wrapper.text()).toContain("事件连接离线");
    expect(feedback.text()).toContain(
      "账号事件连接已断开，页面将使用 HTTP 状态继续工作。"
    );
    await feedback
      .findAll("button")
      .find((button) => button.text() === "重试")
      ?.trigger("click");
    await flushPromises();

    expect(shellMocks.application.eventSocket.retryCurrent).toHaveBeenCalledOnce();
    wrapper.unmount();
  });

  it("向账号页面注入可注销的未保存守卫端口", async () => {
    shellMocks.contextState.currentAccountId = "account-current";
    shellMocks.contextState.currentAccount = workspaceContext("account-current");

    const { wrapper } = await mountShell(GuardProbe);

    expect(wrapper.get('[data-testid="guard-probe"]').exists()).toBe(true);
    expect(shellMocks.application.unsavedGuards.register).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "script-draft",
        label: "脚本草稿",
        isDirty: expect.any(Function),
        save: expect.any(Function),
        discard: expect.any(Function)
      })
    );

    wrapper.unmount();
    expect(shellMocks.unregisterGuard).toHaveBeenCalledOnce();
  });

  it("账号归档事件只在命中当前账号时清空上下文，并始终刷新目录", async () => {
    shellMocks.contextState.currentAccountId = "account-current";
    shellMocks.contextState.currentAccount = workspaceContext("account-current");
    const { wrapper } = await mountShell(WorkspaceProbe);

    window.dispatchEvent(
      new CustomEvent("tk-ops:accounts-changed", {
        detail: {
          accountId: "account-other",
          reason: "archived"
        }
      })
    );
    await flushPromises();

    expect(
      shellMocks.application.context.clearCurrentAccount
    ).not.toHaveBeenCalled();
    expect(shellMocks.directory.load).toHaveBeenCalledTimes(2);

    window.dispatchEvent(
      new CustomEvent("tk-ops:accounts-changed", {
        detail: {
          accountId: "account-current",
          reason: "archived"
        }
      })
    );
    await flushPromises();

    expect(
      shellMocks.application.context.clearCurrentAccount
    ).toHaveBeenCalledOnce();
    expect(shellMocks.directory.load).toHaveBeenCalledTimes(3);
    wrapper.unmount();
  });
});

async function mountShell(component: Component) {
  const accountRoutes = [
    ["/workspace", "工作台"],
    ["/strategy-knowledge", "定位与知识"],
    ["/scripts", "脚本与选题"],
    ["/storyboards", "分镜规划"],
    ["/video-deconstruction", "视频拆解"],
    ["/production/batches", "批量生产"],
    ["/content-library", "内容库"],
    ["/media-tools", "媒体工具箱"],
    ["/publishing", "发布"],
    ["/review", "复盘"]
  ] as const;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      ...accountRoutes.map(([path, title]) => ({
        path,
        component,
        meta: {
          scope: "account",
          title
        }
      })),
      {
        path: "/settings/accounts",
        component: { template: "<section>账号管理</section>" },
        meta: {
          scope: "system",
          title: "账号管理"
        }
      },
      {
        path: "/settings/ai-system",
        component: { template: "<section>AI 与系统设置</section>" },
        meta: {
          scope: "system",
          title: "AI 与系统设置"
        }
      }
    ]
  });
  await router.push("/workspace");
  await router.isReady();
  const wrapper = mount(AccountWorkspaceLayout, {
    attachTo: document.body,
    global: {
      plugins: [createPinia(), router]
    }
  });
  await flushPromises();
  return { router, wrapper };
}

function workspaceContext(accountId: string): AccountWorkspaceContextDto {
  const readinessItem = {
    status: "ready" as const,
    label: "已就绪",
    errorCode: null,
    logId: null,
    checkedAt: null,
    suggestedAction: null
  };
  const account: AccountDto = {
    id: accountId,
    name: "当前账号",
    username: null,
    platform: "tiktok",
    status: "ready",
    positioningSummary: null,
    lastUsedAt: null,
    readiness: {
      connection: { ...readinessItem },
      knowledge: { ...readinessItem },
      ai: { ...readinessItem },
      overall: "ready",
      checkedAt: null,
      suggestedAction: null
    },
    wizardCompletedAt: null,
    revision: 1
  };
  return {
    account,
    readiness: account.readiness,
    navigation: {
      lastRoute: "/workspace",
      availableRoutes: ["account_workspace_home"]
    },
    taskSummary: {
      running: 0,
      failed: 0
    },
    workspaceRevision: 1
  };
}
