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

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "自动化任务操作失败";
}

export const useAutomationStore = defineStore("automation", {
  state: () => ({
    tasks: [] as AutomationTaskDto[],
    runsByTaskId: {} as Record<string, AutomationTaskRunDto[]>,
    lastTriggerResult: null as TriggerTaskResultDto | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadTasks(status?: string, type?: string) {
      this.loading = true;
      this.error = null;
      try {
        this.tasks = await fetchAutomationTasks(status, type);
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load automation tasks", error);
      } finally {
        this.loading = false;
      }
    },
    async addTask(input: AutomationTaskCreateInput) {
      this.error = null;
      try {
        const task = await createAutomationTask(input);
        this.tasks.unshift(task);
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create automation task", error);
        return null;
      }
    },
    async updateTask(id: string, input: AutomationTaskUpdateInput) {
      this.error = null;
      try {
        const task = await updateAutomationTask(id, input);
        this.tasks = this.tasks.map((item) => (item.id === id ? task : item));
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update automation task", error);
        return null;
      }
    },
    async removeTask(id: string) {
      this.error = null;
      try {
        await deleteAutomationTask(id);
        this.tasks = this.tasks.filter((task) => task.id !== id);
        delete this.runsByTaskId[id];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to delete automation task", error);
      }
    },
    async triggerTask(id: string) {
      this.error = null;
      try {
        this.lastTriggerResult = await triggerAutomationTask(id);
        await this.loadRuns(id);
        await this.loadTasks();
        return this.lastTriggerResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to trigger automation task", error);
        return null;
      }
    },
    async loadRuns(id: string) {
      this.error = null;
      try {
        this.runsByTaskId[id] = await fetchAutomationTaskRuns(id);
        return this.runsByTaskId[id];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load automation task runs", error);
        return [];
      }
    }
  }
});
