import { defineStore } from "pinia";

import {
  createDashboardProject,
  fetchDashboardSummary,
  updateCurrentProjectContext,
  deleteDashboardProject
} from "@/app/runtime-client";
import type {
  CreateProjectInput,
  CurrentProjectContext,
  DashboardSummary,
  ProjectSummary,
  RuntimeRequestErrorShape
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export type ProjectStoreStatus = "idle" | "loading" | "ready" | "saving" | "error";

type ProjectStoreState = {
  currentProject: CurrentProjectContext | null;
  error: RuntimeRequestErrorShape | null;
  recentProjects: ProjectSummary[];
  status: ProjectStoreStatus;
};

export const useProjectStore = defineStore("project", {
  state: (): ProjectStoreState => ({
    currentProject: null,
    error: null,
    recentProjects: [],
    status: "idle"
  }),
  getters: {
    hasProjectContext: (state) => state.currentProject !== null,
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading" || state.status === "saving") {
        return "loading";
      }
      if (state.status === "error") {
        return "error";
      }
      return state.currentProject || state.recentProjects.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    async load(): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        this.applySummary(await fetchDashboardSummary());
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async refresh(): Promise<void> {
      await this.load();
    },
    async createProject(input: CreateProjectInput): Promise<ProjectSummary | null> {
      this.status = "saving";
      this.error = null;

      try {
        const created = await createDashboardProject(input);
        this.currentProject = {
          projectId: created.id,
          projectName: created.name,
          status: created.status
        };
        this.recentProjects = [
          created,
          ...this.recentProjects.filter((item) => item.id !== created.id)
        ];
        this.status = "ready";
        return created;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async deleteProject(projectId: string): Promise<boolean> {
      this.status = "saving";
      this.error = null;

      try {
        await deleteDashboardProject(projectId);
        this.recentProjects = this.recentProjects.filter((item) => item.id !== projectId);
        if (this.currentProject?.projectId === projectId) {
          this.currentProject = null;
        }
        this.status = "ready";
        return true;
      } catch (error) {
        this.applyRuntimeError(error);
        return false;
      }
    },
    async selectProject(projectId: string): Promise<CurrentProjectContext | null> {
      this.status = "saving";
      this.error = null;

      try {
        const context = await updateCurrentProjectContext(projectId);
        this.currentProject = context;
        this.recentProjects = [
          ...this.recentProjects.sort((left, right) =>
            left.id === projectId ? -1 : right.id === projectId ? 1 : 0
          )
        ];
        this.status = "ready";
        return context;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    applySummary(summary: DashboardSummary): void {
      this.recentProjects = summary.recentProjects;
      this.currentProject = summary.currentProject;
    },
    applyRuntimeError(error: unknown): void {
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "项目请求失败，请稍后重试。");
    }
  }
});
