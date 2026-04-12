import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  activateLicense,
  fetchLicenseStatus
} from "@/app/runtime-client";
import type {
  LicenseActivationInput,
  LicenseStatus,
  RuntimeRequestErrorShape
} from "@/types/runtime";

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
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("授权请求失败。");

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
