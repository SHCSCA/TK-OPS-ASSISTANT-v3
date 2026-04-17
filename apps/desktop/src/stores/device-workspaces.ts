import { defineStore } from "pinia";
import {
  checkDeviceWorkspaceHealth,
  createBrowserInstance,
  createDeviceWorkspace,
  createExecutionBinding,
  deleteDeviceWorkspace,
  fetchBrowserInstances,
  fetchDeviceWorkspaces,
  fetchExecutionBindings,
  removeBrowserInstance,
  removeExecutionBinding,
  updateDeviceWorkspace
} from "@/app/runtime-client";
import type {
  BrowserInstanceCreateInput,
  BrowserInstanceDto,
  DeviceWorkspaceCreateInput,
  DeviceWorkspaceDto,
  DeviceWorkspaceUpdateInput,
  ExecutionBindingCreateInput,
  ExecutionBindingDto,
  HealthCheckResultDto
} from "@/types/runtime";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "工作区操作失败";
}

export const useDeviceWorkspacesStore = defineStore("device-workspaces", {
  state: () => ({
    workspaces: [] as DeviceWorkspaceDto[],
    browserInstancesByWorkspaceId: {} as Record<string, BrowserInstanceDto[]>,
    bindingsByWorkspaceId: {} as Record<string, ExecutionBindingDto[]>,
    lastHealthCheck: null as HealthCheckResultDto | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadWorkspaces() {
      this.loading = true;
      this.error = null;
      try {
        this.workspaces = await fetchDeviceWorkspaces();
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load device workspaces", error);
      } finally {
        this.loading = false;
      }
    },
    async addWorkspace(input: DeviceWorkspaceCreateInput) {
      this.error = null;
      try {
        const workspace = await createDeviceWorkspace(input);
        this.workspaces.unshift(workspace);
        return workspace;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create device workspace", error);
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
        return workspace;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update device workspace", error);
        return null;
      }
    },
    async removeWorkspace(id: string) {
      this.error = null;
      try {
        await deleteDeviceWorkspace(id);
        this.workspaces = this.workspaces.filter((workspace) => workspace.id !== id);
        delete this.browserInstancesByWorkspaceId[id];
        delete this.bindingsByWorkspaceId[id];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to delete device workspace", error);
      }
    },
    async checkHealth(id: string) {
      this.error = null;
      try {
        this.lastHealthCheck = await checkDeviceWorkspaceHealth(id);
        await this.loadWorkspaces();
        return this.lastHealthCheck;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to check device workspace health", error);
        return null;
      }
    },
    async loadBrowserInstances(workspaceId: string) {
      this.error = null;
      try {
        this.browserInstancesByWorkspaceId[workspaceId] = await fetchBrowserInstances(
          workspaceId
        );
        return this.browserInstancesByWorkspaceId[workspaceId];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load browser instances", error);
        return [];
      }
    },
    async addBrowserInstance(input: BrowserInstanceCreateInput) {
      this.error = null;
      try {
        const instance = await createBrowserInstance(input);
        const list = this.browserInstancesByWorkspaceId[input.workspace_id] ?? [];
        this.browserInstancesByWorkspaceId[input.workspace_id] = [instance, ...list];
        return instance;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create browser instance", error);
        return null;
      }
    },
    async removeBrowserInstance(id: string) {
      this.error = null;
      try {
        await removeBrowserInstance(id);
        for (const workspaceId of Object.keys(this.browserInstancesByWorkspaceId)) {
          this.browserInstancesByWorkspaceId[workspaceId] =
            this.browserInstancesByWorkspaceId[workspaceId].filter(
              (item) => item.id !== id
            );
        }
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to remove browser instance", error);
      }
    },
    async loadBindings(deviceWorkspaceId: string, accountId?: string) {
      this.error = null;
      try {
        this.bindingsByWorkspaceId[deviceWorkspaceId] = await fetchExecutionBindings(
          deviceWorkspaceId,
          accountId
        );
        return this.bindingsByWorkspaceId[deviceWorkspaceId];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load execution bindings", error);
        return [];
      }
    },
    async addBinding(input: ExecutionBindingCreateInput) {
      this.error = null;
      try {
        const binding = await createExecutionBinding(input);
        const list = this.bindingsByWorkspaceId[input.device_workspace_id] ?? [];
        this.bindingsByWorkspaceId[input.device_workspace_id] = [binding, ...list];
        return binding;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create execution binding", error);
        return null;
      }
    },
    async removeBinding(id: string) {
      this.error = null;
      try {
        await removeExecutionBinding(id);
        for (const workspaceId of Object.keys(this.bindingsByWorkspaceId)) {
          this.bindingsByWorkspaceId[workspaceId] = this.bindingsByWorkspaceId[
            workspaceId
          ].filter((item) => item.id !== id);
        }
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to remove execution binding", error);
      }
    }
  }
});
