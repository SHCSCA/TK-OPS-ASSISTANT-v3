import { onBeforeUnmount, readonly, ref } from "vue";

import { onDesktopRuntimeConnectionRecovered } from "@/app/runtime-client/connection";
import { isRuntimeRequestAborted, RuntimeError } from "@/app/runtime-client/core";
import { listAccountTasks } from "@/app/runtime-client/tasks";
import type { RuntimeEventDto } from "@/types/runtime/events";
import type { RuntimeTaskDto } from "@/types/runtime/tasks";

type ProjectionState = "idle" | "loading" | "ready" | "empty" | "error";

export function useAccountTaskProjection() {
  const accountId = ref<string | null>(null);
  const tasks = ref<RuntimeTaskDto[]>([]);
  const state = ref<ProjectionState>("idle");
  const error = ref<RuntimeError | null>(null);
  let controller: AbortController | null = null;
  let refreshTimer: number | null = null;

  const removeRecoveryListener = onDesktopRuntimeConnectionRecovered(async () => {
    if (accountId.value) await load(accountId.value);
  });

  onBeforeUnmount(dispose);

  async function load(nextAccountId: string | null): Promise<void> {
    controller?.abort();
    controller = null;
    accountId.value = nextAccountId;
    error.value = null;
    if (!nextAccountId) {
      tasks.value = [];
      state.value = "idle";
      return;
    }
    const active = new AbortController();
    controller = active;
    state.value = tasks.value.length > 0 ? "ready" : "loading";
    try {
      const result = await listAccountTasks(nextAccountId, 50, {
        signal: active.signal
      });
      if (active.signal.aborted || accountId.value !== nextAccountId) return;
      tasks.value = result.data.items;
      state.value = tasks.value.length > 0 ? "ready" : "empty";
    } catch (cause) {
      if (isRuntimeRequestAborted(cause) || accountId.value !== nextAccountId) return;
      error.value = cause instanceof RuntimeError
        ? cause
        : new RuntimeError("账号任务状态加载失败，请稍后重试。", {
          errorCode: "INTERNAL_ERROR",
          status: 500
        });
      state.value = "error";
    } finally {
      if (controller === active) controller = null;
    }
  }

  function handleEvent(event: RuntimeEventDto): void {
    if (
      !accountId.value
      || event.accountId !== accountId.value
      || event.topic !== `account:${accountId.value}:tasks`
    ) {
      return;
    }
    scheduleRefresh();
  }

  function scheduleRefresh(): void {
    if (refreshTimer !== null) window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(() => {
      refreshTimer = null;
      void load(accountId.value);
    }, 180);
  }

  function dispose(): void {
    controller?.abort();
    controller = null;
    if (refreshTimer !== null) window.clearTimeout(refreshTimer);
    refreshTimer = null;
    removeRecoveryListener();
  }

  return {
    accountId: readonly(accountId),
    error: readonly(error),
    handleEvent,
    load,
    state: readonly(state),
    tasks: readonly(tasks)
  };
}
