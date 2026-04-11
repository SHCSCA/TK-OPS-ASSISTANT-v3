import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  createDashboardProject,
  fetchDashboardSummary,
  updateCurrentProjectContext
} from "@/app/runtime-client";
import type {
  CreateProjectInput,
  CurrentProjectContext,
  DashboardSummary,
  ProjectSummary,
  RuntimeRequestErrorShape
} from "@/types/runtime";

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
    hasProjectContext: (state) => state.currentProject !== null
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
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("Project request failed.");

      this.status = "error";
      this.error = {
        details: runtimeError.details,
        message: runtimeError.message,
        requestId: runtimeError.requestId,
        status: runtimeError.status
      };
    }
  }
});
