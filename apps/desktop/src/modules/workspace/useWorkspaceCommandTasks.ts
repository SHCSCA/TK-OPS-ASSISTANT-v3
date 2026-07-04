import { computed, onMounted, ref, watch, type ComputedRef } from "vue";

import type { MagicCutReadiness } from "@/modules/workspace/useMagicCutReadiness";
import { useEditingWorkspaceStore } from "@/stores/editing-workspace";
import { useTaskBusStore } from "@/stores/task-bus";
import type { TaskInfo } from "@/types/task-events";

type UseWorkspaceCommandTasksOptions = {
  currentProjectId: ComputedRef<string>;
  magicCutReadiness: ComputedRef<MagicCutReadiness>;
  workspaceStore: ReturnType<typeof useEditingWorkspaceStore>;
};

const workspaceTaskTypes = new Set(["ai-workspace-command", "magic_cut", "ai-magic-cut"]);

export function useWorkspaceCommandTasks(options: UseWorkspaceCommandTasksOptions) {
  const taskBusStore = useTaskBusStore();
  const isCommandCancelPending = ref(false);
  const handledCommandTerminalKeys = new Set<string>();

  const activeTask = computed(() => {
    if (!options.currentProjectId.value) {
      return null;
    }

    for (const task of taskBusStore.tasks.values()) {
      if (isCurrentWorkspaceCommandTask(task) && (task.status === "queued" || task.status === "running")) {
        return task;
      }
    }

    return null;
  });

  const isGenerating = computed(() => {
    return Boolean(activeTask.value) || options.workspaceStore.status === "saving";
  });

  onMounted(() => {
    if (typeof WebSocket !== "undefined") {
      taskBusStore.connect();
    }
  });

  watch(
    () => Array.from(taskBusStore.tasks.values()).map((task) => `${task.id}:${task.status}:${task.updated_at}:${task.message}`).join("|"),
    () => {
      for (const task of taskBusStore.tasks.values()) {
        if (!isCurrentWorkspaceCommandTask(task) || !isTerminalCommandStatus(task.status)) continue;

        const key = `${task.id}:${task.status}:${task.updated_at}:${task.message}`;
        if (handledCommandTerminalKeys.has(key)) continue;
        handledCommandTerminalKeys.add(key);
        void options.workspaceStore.applyCommandTerminalTask(task);
      }
    },
    { immediate: true }
  );

  async function handleMagicCut(): Promise<void> {
    if (!options.currentProjectId.value) return;

    if (!options.magicCutReadiness.value.available) {
      options.workspaceStore.applyBlockedMessage(options.magicCutReadiness.value.message);
      return;
    }

    const result = await options.workspaceStore.runMagicCut(options.currentProjectId.value);
    if (result?.task?.id) {
      const taskId = result.task.id;

      // 从 HTTP 响应直接写入 TaskBus，绕过 WebSocket 竞态窗口
      const raw = result.task;
      const now = new Date().toISOString();
      taskBusStore.tasks.set(taskId, {
        id: taskId,
        task_type: raw.task_type ?? "ai-workspace-command",
        project_id: options.currentProjectId.value ?? null,
        status: raw.status ?? "queued",
        progress: raw.progress ?? 0,
        message: raw.message ?? "AI 命令已进入任务队列。",
        created_at: raw.created_at ?? now,
        updated_at: now,
      });
    }
  }

  async function handleCancelCommandTask(taskId: string): Promise<void> {
    if (!taskId || isCommandCancelPending.value) return;

    isCommandCancelPending.value = true;
    try {
      const result = await options.workspaceStore.cancelCommandTask(taskId);
      if (result?.task) {
        const existingTask = taskBusStore.tasks.get(taskId);
        taskBusStore.tasks.set(taskId, {
          ...(existingTask ?? result.task),
          status: result.task.status,
          progress: result.task.progress,
          message: result.message,
          updated_at: result.task.updated_at
        });
      }
    } finally {
      isCommandCancelPending.value = false;
    }
  }

  function isCurrentWorkspaceCommandTask(task: TaskInfo): boolean {
    return task.project_id === options.currentProjectId.value && workspaceTaskTypes.has(task.task_type);
  }

  function isTerminalCommandStatus(status: TaskInfo["status"]): boolean {
    return status === "succeeded" || status === "failed" || status === "cancelled";
  }

  return {
    activeTask,
    handleCancelCommandTask,
    handleMagicCut,
    isCommandCancelPending,
    isGenerating
  };
}
