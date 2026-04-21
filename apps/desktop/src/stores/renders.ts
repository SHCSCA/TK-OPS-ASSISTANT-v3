import { defineStore } from "pinia";
import {
  cancelRenderTask,
  createRenderTask,
  deleteRenderTask,
  fetchRenderTasks,
  updateRenderTask
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  CancelRenderResultDto,
  RenderTaskCreateInput,
  RenderTaskDto,
  RenderTaskUpdateInput
} from "@/types/runtime";
import type { TaskEvent } from "@/types/task-events";
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "渲染任务操作失败，请稍后重试。");
}

export const useRendersStore = defineStore("renders", {
  state: () => ({
    tasks: [] as RenderTaskDto[],
    lastCancelResult: null as CancelRenderResultDto | null,
    loading: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    error: null as string | null,
    _unsubscribers: {} as Record<string, () => void>
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.tasks.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    initializeWebSocket(): void {
      useTaskBusStore().connect();
    },
    syncSubscriptions(): void {
      const taskBus = useTaskBusStore();
      this.tasks.forEach((task) => {
        // Subscribe only to unfinished tasks to save memory
        const isUnfinished = task.status === "queued" || task.status === "running" || task.status === "pending";
        if (isUnfinished && !this._unsubscribers[task.id]) {
          this._unsubscribers[task.id] = taskBus.subscribe(task.id, (event: TaskEvent) => {
            // When task completes or fails, reload to get output_path and final status
            if (event.type === "task.completed" || event.type === "task.failed") {
              void this.loadTasks();
            }
          });
        }
      });
    },
    async loadTasks(status?: string) {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.tasks = await fetchRenderTasks(status);
        this.status = resolveCollectionStatus(this.tasks.length);
        this.syncSubscriptions();
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async addTask(input: RenderTaskCreateInput) {
      this.error = null;
      try {
        const task = await createRenderTask(input);
        this.tasks.unshift(task);
        this.status = "ready";
        this.syncSubscriptions();
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async updateTask(id: string, input: RenderTaskUpdateInput) {
      this.error = null;
      try {
        const task = await updateRenderTask(id, input);
        this.tasks = this.tasks.map((item) => (item.id === id ? task : item));
        this.status = "ready";
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async removeTask(id: string) {
      this.error = null;
      try {
        await deleteRenderTask(id);
        this.tasks = this.tasks.filter((task) => task.id !== id);
        this.status = this.tasks.length > 0 ? "ready" : "empty";
        if (this._unsubscribers[id]) {
          this._unsubscribers[id]();
          delete this._unsubscribers[id];
        }
      } catch (error) {
        this.error = getErrorMessage(error);
      }
    },
    async cancel(id: string) {
      this.error = null;
      try {
        this.lastCancelResult = await cancelRenderTask(id);
        await this.loadTasks();
        return this.lastCancelResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    }
  }
});
