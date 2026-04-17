import { defineStore } from "pinia";
import {
  createAutomationTask,
  deleteAutomationTask,
  fetchAutomationTaskRuns,
  fetchAutomationTasks,
  triggerAutomationTask,
  updateAutomationTask
} from "@/app/runtime-client";
import type {
  AutomationTaskCreateInput,
  AutomationTaskDto,
  AutomationTaskRunDto,
  AutomationTaskUpdateInput,
  TriggerTaskResultDto
} from "@/types/runtime";
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "自动化任务操作失败，请稍后重试。");
}

export const useAutomationStore = defineStore("automation", {
  state: () => ({
    tasks: [] as AutomationTaskDto[],
    runsByTaskId: {} as Record<string, AutomationTaskRunDto[]>,
    runsStatusByTaskId: {} as Record<string, "idle" | "loading" | "ready" | "error">,
    lastTriggerResult: null as TriggerTaskResultDto | null,
    loading: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    triggerState: "idle" as "idle" | "running" | "ready" | "error",
    error: null as string | null
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.tasks.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    async loadTasks(status?: string, type?: string) {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.tasks = await fetchAutomationTasks(status, type);
        this.status = resolveCollectionStatus(this.tasks.length);
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async addTask(input: AutomationTaskCreateInput) {
      this.error = null;
      try {
        const task = await createAutomationTask(input);
        this.tasks.unshift(task);
        this.status = "ready";
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async updateTask(id: string, input: AutomationTaskUpdateInput) {
      this.error = null;
      try {
        const task = await updateAutomationTask(id, input);
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
        await deleteAutomationTask(id);
        this.tasks = this.tasks.filter((task) => task.id !== id);
        delete this.runsByTaskId[id];
        delete this.runsStatusByTaskId[id];
        this.status = this.tasks.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.error = getErrorMessage(error);
      }
    },
    async triggerTask(id: string) {
      this.error = null;
      this.triggerState = "running";
      try {
        this.lastTriggerResult = await triggerAutomationTask(id);
        await this.loadRuns(id);
        await this.loadTasks();
        this.triggerState = "ready";
        return this.lastTriggerResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.triggerState = "error";
        return null;
      }
    },
    async loadRuns(id: string) {
      this.error = null;
      this.runsStatusByTaskId[id] = "loading";
      try {
        this.runsByTaskId[id] = await fetchAutomationTaskRuns(id);
        this.runsStatusByTaskId[id] = "ready";
        return this.runsByTaskId[id];
      } catch (error) {
        this.error = getErrorMessage(error);
        this.runsStatusByTaskId[id] = "error";
        return [];
      }
    }
  }
});
