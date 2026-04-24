import { defineStore } from "pinia";
import {
  checkDeviceWorkspaceHealth,
  createDeviceWorkspace,
  deleteDeviceWorkspace,
  fetchDeviceWorkspaces,
  updateDeviceWorkspace,
  fetchBrowserInstances,
  createBrowserInstance,
  removeBrowserInstance
} from "@/app/runtime-client";
import type {
  DeviceWorkspaceCreateInput,
  DeviceWorkspaceDto,
  DeviceWorkspaceUpdateInput,
  HealthCheckResultDto,
  BrowserInstanceDto,
  BrowserInstanceCreateInput
} from "@/types/runtime";
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "工作区操作失败，请稍后重试。");
}

export const useDeviceWorkspacesStore = defineStore("device-workspaces", {
  state: () => ({
    workspaces: [] as DeviceWorkspaceDto[],
    browserInstances: [] as BrowserInstanceDto[],
    lastHealthCheck: null as HealthCheckResultDto | null,
    loading: false,
    instancesLoading: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    healthCheckState: "idle" as "idle" | "checking" | "ready" | "error",
    error: null as string | null
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.workspaces.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    async loadWorkspaces() {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.workspaces = await fetchDeviceWorkspaces();
        this.status = resolveCollectionStatus(this.workspaces.length);
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async addWorkspace(input: DeviceWorkspaceCreateInput) {
      this.error = null;
      try {
        const workspace = await createDeviceWorkspace(input);
        this.workspaces.unshift(workspace);
        this.status = "ready";
        return workspace;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async updateWorkspace(id: string, input: DeviceWorkspaceUpdateInput) {
      this.error = null;
      try {
        const workspace = await updateDeviceWorkspace(id, input);
        this.workspaces = this.workspaces.map((item) =>
          item.id === id ? workspace : item
        );
        this.status = "ready";
        return workspace;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async removeWorkspace(id: string) {
      this.error = null;
      try {
        await deleteDeviceWorkspace(id);
        this.workspaces = this.workspaces.filter((workspace) => workspace.id !== id);
        this.status = this.workspaces.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.error = getErrorMessage(error);
      }
    },
    async checkHealth(id: string) {
      this.error = null;
      this.healthCheckState = "checking";
      try {
        this.lastHealthCheck = await checkDeviceWorkspaceHealth(id);
        await this.loadWorkspaces();
        this.healthCheckState = "ready";
        return this.lastHealthCheck;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.healthCheckState = "error";
        return null;
      }
    },
    async loadBrowserInstances(workspaceId: string) {
      this.instancesLoading = true;
      try {
        this.browserInstances = await fetchBrowserInstances(workspaceId);
      } catch (error) {
        this.error = getErrorMessage(error);
      } finally {
        this.instancesLoading = false;
      }
    },
    async addBrowserInstance(workspaceId: string, input: BrowserInstanceCreateInput) {
      this.error = null;
      try {
        const instance = await createBrowserInstance(workspaceId, input);
        this.browserInstances.unshift(instance);
        return instance;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async deleteBrowserInstance(id: string) {
      this.error = null;
      try {
        await removeBrowserInstance(id);
        this.browserInstances = this.browserInstances.filter(i => i.id !== id);
      } catch (error) {
        this.error = getErrorMessage(error);
      }
    }
  }
});
