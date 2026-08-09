import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  accountContextApplication,
  consoleAccountContextLogger,
  useAccountDirectoryStore
} from "@/app/account-context";
import {
  ACCOUNTS_CHANGED_EVENT,
  type AccountDirectoryChangeReason
} from "@/modules/accounts/account-directory-events";
import { useAccountTaskProjection } from "@/modules/tasks/use-account-task-projection";

import {
  createNavigationItems,
  mergeCurrentAccount,
  readCompactWindow,
  readQueryAccount,
  switchStatusMessage,
  toSwitcherOption
} from "./account-workspace-shell-helpers";
import type { ShellFeedback } from "./account-workspace-types";

export function useAccountWorkspaceShell() {
  const route = useRoute();
  const router = useRouter();
  const directory = useAccountDirectoryStore();
  const application = accountContextApplication;
  const taskProjection = useAccountTaskProjection();
  const contextState = application.context.state;
  const switcherOpen = ref(false);
  const initializing = ref(true);
  const compact = ref(readCompactWindow());
  const themeMedia =
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-color-scheme: dark)")
      : null;
  const systemDark = ref(themeMedia?.matches ?? false);
  const manualFeedback = ref<ShellFeedback | null>(null);
  let removeEventListener: (() => void) | null = null;
  let previousPath = route.path;

  const workspaceItems = createNavigationItems(true);
  const systemItems = createNavigationItems(false);
  const isAccountRoute = computed(
    () => route.meta.scope === "account"
  );
  const currentContext = computed(() => contextState.currentAccount);
  const routeBoundContext = computed(() => {
    const requested = readQueryAccount(route.query.account);
    if (
      requested
      && requested !== contextState.currentAccountId
    ) {
      return null;
    }
    return currentContext.value;
  });
  const currentAccountDto = computed(
    () => currentContext.value?.account ?? null
  );
  const accountOptions = computed(() =>
    mergeCurrentAccount(directory.accounts, currentAccountDto.value).map(
      toSwitcherOption
    )
  );
  const currentAccount = computed(() => {
    const account = currentAccountDto.value;
    return account ? toSwitcherOption(account) : null;
  });
  const switchBusy = computed(
    () =>
      initializing.value
      || (
        contextState.switchStatus !== "idle"
        && contextState.switchStatus !== "failed"
      )
  );
  const pageTitle = computed(() =>
    typeof route.meta.title === "string" ? route.meta.title : "TK-OPS"
  );
  const runtimeTone = computed(() => {
    switch (application.eventSocket.state.status) {
      case "online":
        return "online" as const;
      case "connecting":
        return "loading" as const;
      case "offline":
      case "error":
        return "offline" as const;
      default:
        return "idle" as const;
    }
  });
  const runtimeLabel = computed(() => {
    switch (application.eventSocket.state.status) {
      case "online":
        return "Runtime 正常";
      case "connecting":
        return "Runtime 连接中";
      case "offline":
        return "事件连接离线";
      case "error":
        return "Runtime 异常";
      default:
        return currentAccountDto.value ? "事件连接待命" : "未选择账号";
    }
  });
  const currentTheme = computed<"light" | "dark">(() => {
    const preference = application.uiConfig.state.theme;
    if (preference === "light" || preference === "dark") return preference;
    return systemDark.value ? "dark" : "light";
  });
  const themeIcon = computed(() =>
    currentTheme.value === "dark" ? "light_mode" : "dark_mode"
  );
  const themeActionLabel = computed(() =>
    currentTheme.value === "dark" ? "切换浅色主题" : "切换深色主题"
  );
  const feedback = computed<ShellFeedback>(() => {
    if (manualFeedback.value) return manualFeedback.value;
    if (contextState.error) {
      return {
        id: "context",
        tone: "danger",
        message: contextState.error.message,
        logId: contextState.error.logId,
        retryable: contextState.error.retryable
      };
    }
    if (application.navigationState.error) {
      return {
        id: "navigation",
        tone: "danger",
        message: application.navigationState.error.message,
        logId: application.navigationState.error.logId,
        retryable: false
      };
    }
    if (directory.error) {
      return {
        id: "directory",
        tone: "danger",
        message: directory.error.message,
        logId: directory.error.logId,
        retryable: directory.error.retryable
      };
    }
    if (application.uiConfig.state.error) {
      return {
        id: "config",
        tone: "danger",
        message: application.uiConfig.state.error.message,
        logId: application.uiConfig.state.error.logId,
        retryable: application.uiConfig.state.error.retryable
      };
    }
    if (application.eventSocket.state.error) {
      return {
        id: "socket",
        tone: "warning",
        message: application.eventSocket.state.error.message,
        retryable: true
      };
    }
    if (switchBusy.value) {
      return {
        id: "switching",
        tone: "info",
        message: switchStatusMessage(contextState.switchStatus)
      };
    }
    const context = currentContext.value;
    if (!context) {
      return {
        id: "no-account",
        tone: "info",
        message: "选择账号后，定位、知识、内容和任务会在同一工作区内切换。"
      };
    }
    if (context.taskSummary.failed > 0) {
      return {
        id: "failed-tasks",
        tone: "warning",
        message: `当前账号有 ${context.taskSummary.failed} 个失败任务，请进入对应页面处理。`
      };
    }
    return {
      id: "ready",
      tone: context.readiness.overall === "ready" ? "info" : "warning",
      message:
        context.taskSummary.running > 0
          ? `当前账号有 ${context.taskSummary.running} 个任务正在运行。`
          : "账号上下文已隔离，当前没有运行中的任务。"
    };
  });

  watch(
    () => currentAccountDto.value?.revision,
    () => {
      const account = currentAccountDto.value;
      if (account) directory.merge(account);
    }
  );

  watch(
    () => currentAccountDto.value?.id ?? null,
    (accountId) => void taskProjection.load(accountId)
  );

  watch(
    () => route.fullPath,
    async () => {
      switcherOpen.value = false;
      const nextPath = route.path;
      if (
        previousPath === "/settings/accounts"
        || nextPath === "/settings/accounts"
      ) {
        await directory.load();
      }
      previousPath = nextPath;
      await selectRequestedAccount();
    }
  );

  onMounted(async () => {
    window.addEventListener("resize", updateCompactWindow);
    themeMedia?.addEventListener?.("change", updateSystemTheme);
    window.addEventListener(
      ACCOUNTS_CHANGED_EVENT,
      handleAccountsChanged
    );
    removeEventListener = application.eventSocket.onEvent((event) => {
      taskProjection.handleEvent(event);
      const account = currentAccountDto.value;
      if (account) directory.merge(account);
    });
    try {
      await Promise.all([directory.load(), application.initialize()]);
      initializing.value = false;
      await selectRequestedAccount();
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 初始化账号工作区失败",
        error
      );
    } finally {
      initializing.value = false;
    }
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", updateCompactWindow);
    themeMedia?.removeEventListener?.("change", updateSystemTheme);
    window.removeEventListener(
      ACCOUNTS_CHANGED_EVENT,
      handleAccountsChanged
    );
    removeEventListener?.();
  });

  async function switchAccount(accountId: string): Promise<void> {
    switcherOpen.value = false;
    try {
      const result = await application.context.switchAccount(accountId);
      if (result.status === "switched" || result.status === "unchanged") {
        const account = currentAccountDto.value;
        if (account) directory.merge(account);
      }
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 切换账号工作区失败",
        error
      );
      manualFeedback.value = {
        id: "switch-unhandled",
        tone: "danger",
        message: "账号切换失败，请重新加载工作区后再试。",
        retryable: false
      };
    }
  }

  async function selectRequestedAccount(): Promise<void> {
    if (initializing.value) return;
    const requested = readQueryAccount(route.query.account);
    if (!requested || requested === contextState.currentAccountId) return;
    try {
      await application.context.switchAccount(requested, {
        preferredRoute: route.fullPath
      });
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 打开指定账号工作区失败",
        error
      );
    }
  }

  async function openAccountManagement(add = false): Promise<void> {
    switcherOpen.value = false;
    await router.push({
      path: "/settings/accounts",
      query: add ? { action: "add" } : {}
    });
  }

  async function retry(feedbackId: string): Promise<void> {
    manualFeedback.value = null;
    try {
      switch (feedbackId) {
        case "context":
          await application.context.retryLastFailure();
          return;
        case "directory":
          await directory.load();
          return;
        case "config":
          await application.uiConfig.load();
          return;
        case "socket":
          await application.eventSocket.retryCurrent();
          return;
      }
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 重试工作区操作失败",
        error
      );
      manualFeedback.value = {
        id: "retry-failed",
        tone: "danger",
        message: "重试失败，请确认本机 Runtime 状态后再试。"
      };
    }
  }

  async function toggleTheme(): Promise<void> {
    try {
      await application.uiConfig.toggleTheme();
    } catch (error) {
      consoleAccountContextLogger.error(
        "[account-shell] 切换主题失败",
        error
      );
    }
  }

  function showLog(logId: string): void {
    manualFeedback.value = {
      id: "log-reference",
      tone: "info",
      message: `日志编号：${logId}。可在“AI 与系统设置”的诊断区检索。`
    };
  }

  function updateCompactWindow(): void {
    compact.value = readCompactWindow();
  }

  function updateSystemTheme(event: MediaQueryListEvent): void {
    systemDark.value = event.matches;
  }

  function handleAccountsChanged(event: Event): void {
    void reconcileAccountDirectoryChange(event);
  }

  async function reconcileAccountDirectoryChange(event: Event): Promise<void> {
    const detail = (
      event as CustomEvent<{
        accountId?: string;
        reason?: AccountDirectoryChangeReason;
      }>
    ).detail;
    if (
      detail?.reason === "archived"
      && detail.accountId === contextState.currentAccountId
    ) {
      try {
        await application.context.clearCurrentAccount();
      } catch (error) {
        consoleAccountContextLogger.error(
          "[account-shell] 清空已归档账号上下文失败",
          error
        );
        manualFeedback.value = {
          id: "archive-context-clear",
          tone: "danger",
          message: "账号已归档，但工作区清理不完整，请重启应用后重试。"
        };
      }
    }
    await directory.load();
  }

  return {
    accountOptions,
    application,
    compact,
    currentAccount,
    currentAccountDto,
    currentContext,
    directory,
    feedback,
    initializing,
    isAccountRoute,
    openAccountManagement,
    pageTitle,
    retry,
    runtimeLabel,
    runtimeTone,
    routeBoundContext,
    showLog,
    switchAccount,
    switchBusy,
    switcherOpen,
    systemItems,
    taskProjection,
    themeActionLabel,
    themeIcon,
    toggleTheme,
    workspaceItems
  };
}
