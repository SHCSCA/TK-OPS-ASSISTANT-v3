import { defineStore } from "pinia";
import {
  checkDeviceWorkspaceHealth,
  createDeviceWorkspace,
  deleteDeviceWorkspace,
  fetchDeviceWorkspaces,
  updateDeviceWorkspace
} from "@/app/runtime-client";
import type {
  DeviceWorkspaceCreateInput,
  DeviceWorkspaceDto,
  DeviceWorkspaceUpdateInput,
  HealthCheckResultDto
} from "@/types/runtime";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "工作区操作失败";
}

export const useDeviceWorkspacesStore = defineStore("device-workspaces", {
  state: () => ({
    workspaces: [] as DeviceWorkspaceDto[],
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
    }
  }
});
