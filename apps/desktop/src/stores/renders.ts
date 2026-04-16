import { defineStore } from "pinia";
import {
  cancelRenderTask,
  createRenderTask,
  deleteRenderTask,
  fetchRenderTasks,
  updateRenderTask
} from "@/app/runtime-client";
import type {
  CancelRenderResultDto,
  RenderTaskCreateInput,
  RenderTaskDto,
  RenderTaskUpdateInput
} from "@/types/runtime";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "渲染任务操作失败";
}

export const useRendersStore = defineStore("renders", {
  state: () => ({
    tasks: [] as RenderTaskDto[],
    lastCancelResult: null as CancelRenderResultDto | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadTasks(status?: string) {
      this.loading = true;
      this.error = null;
      try {
        this.tasks = await fetchRenderTasks(status);
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load render tasks", error);
      } finally {
        this.loading = false;
      }
    },
    async addTask(input: RenderTaskCreateInput) {
      this.error = null;
      try {
        const task = await createRenderTask(input);
        this.tasks.unshift(task);
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create render task", error);
        return null;
      }
    },
    async updateTask(id: string, input: RenderTaskUpdateInput) {
      this.error = null;
      try {
        const task = await updateRenderTask(id, input);
        this.tasks = this.tasks.map((item) => (item.id === id ? task : item));
        return task;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update render task", error);
        return null;
      }
    },
    async removeTask(id: string) {
      this.error = null;
      try {
        await deleteRenderTask(id);
        this.tasks = this.tasks.filter((task) => task.id !== id);
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to delete render task", error);
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
        console.error("Failed to cancel render task", error);
        return null;
      }
    }
  }
});
