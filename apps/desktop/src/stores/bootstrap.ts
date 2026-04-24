import { defineStore } from "pinia";

import { hasCompletedBootstrapInitialization } from "@/bootstrap/bootstrap-form";
import type { AppSettingsUpdateInput, LicenseActivationInput } from "@/types/runtime";

import { useConfigBusStore } from "./config-bus";
import { useLicenseStore } from "./license";

export type BootstrapPhase =
  | "boot_loading"
  | "boot_error"
  | "license_required"
  | "initialization_required"
  | "ready";

type BootstrapState = {
  phase: BootstrapPhase;
};

export const useBootstrapStore = defineStore("bootstrap", {
  state: (): BootstrapState => ({
    phase: "boot_loading"
  }),
  actions: {
    async load(): Promise<void> {
      const configBusStore = useConfigBusStore();
      const licenseStore = useLicenseStore();
      const tasks: Array<Promise<void>> = [];

      this.phase = "boot_loading";

      if (configBusStore.status === "idle") {
        tasks.push(configBusStore.load());
      }

      if (licenseStore.status === "idle") {
        tasks.push(licenseStore.loadStatus());
      }

      if (tasks.length > 0) {
        await Promise.all(tasks);
      }

      this.syncPhase();
    },
    async retry(): Promise<void> {
      const configBusStore = useConfigBusStore();
      const licenseStore = useLicenseStore();

      this.phase = "boot_loading";
      await Promise.all([configBusStore.refresh(), licenseStore.loadStatus()]);
      this.syncPhase();
    },
    async activateLicense(input: LicenseActivationInput): Promise<boolean> {
      const licenseStore = useLicenseStore();

      await licenseStore.activate(input);
      this.syncPhase();
      return licenseStore.active;
    },
    async completeInitialization(input: AppSettingsUpdateInput): Promise<boolean> {
      const configBusStore = useConfigBusStore();

      await configBusStore.save(input);
      this.syncPhase();
      return this.phase === "ready";
    },
    syncPhase(): void {
      const configBusStore = useConfigBusStore();
      const licenseStore = useLicenseStore();
      const hasSettings = Boolean(configBusStore.settings);

      if (
        configBusStore.runtimeStatus === "loading" ||
        configBusStore.status === "idle" ||
        configBusStore.status === "loading" ||
        licenseStore.status === "idle" ||
        licenseStore.status === "loading" ||
        licenseStore.status === "submitting"
      ) {
        this.phase = "boot_loading";
        return;
      }

      if (configBusStore.runtimeStatus === "offline") {
        this.phase = "boot_error";
        return;
      }

      if (!licenseStore.active) {
        this.phase = "license_required";
        return;
      }

      if (licenseStore.status === "error") {
        this.phase = "license_required";
        return;
      }

      if (configBusStore.status === "error" && !hasSettings) {
        this.phase = "boot_error";
        return;
      }

      if (!hasCompletedBootstrapInitialization(configBusStore.settings)) {
        this.phase = "initialization_required";
        return;
      }

      this.phase = "ready";
    }
  }
});

