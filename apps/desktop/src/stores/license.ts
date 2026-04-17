import { defineStore } from "pinia";

import {
  activateLicense,
  fetchLicenseStatus
} from "@/app/runtime-client";
import type {
  LicenseActivationInput,
  LicenseStatus,
  RuntimeRequestErrorShape
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export type LicenseStoreStatus = "idle" | "loading" | "ready" | "submitting" | "error";

type LicenseState = LicenseStatus & {
  error: RuntimeRequestErrorShape | null;
  status: LicenseStoreStatus;
};

function createDefaultLicenseState(): LicenseState {
  return {
    activatedAt: null,
    active: false,
    error: null,
    machineBound: false,
    machineCode: "",
    maskedCode: "",
    licenseType: "perpetual",
    restrictedMode: true,
    status: "idle"
  };
}

export const useLicenseStore = defineStore("license", {
  state: (): LicenseState => createDefaultLicenseState(),
  getters: {
    viewState: (state): "loading" | "blocked" | "ready" | "error" => {
      if (state.status === "loading" || state.status === "submitting") {
        return "loading";
      }
      if (state.status === "error") {
        return "error";
      }
      return !state.active && state.restrictedMode ? "blocked" : "ready";
    }
  },
  actions: {
    async loadStatus(): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        this.applyLicenseStatus(await fetchLicenseStatus());
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async activate(input: LicenseActivationInput): Promise<void> {
      this.status = "submitting";
      this.error = null;

      try {
        this.applyLicenseStatus(await activateLicense(input));
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyLicenseStatus(status: LicenseStatus): void {
      this.activatedAt = status.activatedAt;
      this.active = status.active;
      this.machineBound = status.machineBound;
      this.machineCode = status.machineCode;
      this.licenseType = status.licenseType;
      this.maskedCode = status.maskedCode;
      this.restrictedMode = status.restrictedMode;
    },
    applyRuntimeError(error: unknown): void {
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "授权请求失败，请稍后重试。");
    }
  }
});
