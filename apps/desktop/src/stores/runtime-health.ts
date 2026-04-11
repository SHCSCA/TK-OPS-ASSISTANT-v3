import { defineStore } from "pinia";

import { fetchRuntimeHealth } from "@/app/runtime-client";
import type { RuntimeHealthSnapshot } from "@/types/runtime";

export type RuntimeHealthStatus = "idle" | "loading" | "online" | "offline";

type RuntimeHealthState = {
  error: string;
  snapshot: RuntimeHealthSnapshot | null;
  status: RuntimeHealthStatus;
};

export const useRuntimeHealthStore = defineStore("runtime-health", {
  state: (): RuntimeHealthState => ({
    error: "",
    snapshot: null,
    status: "idle"
  }),
  actions: {
    async refresh(): Promise<void> {
      this.status = "loading";
      this.error = "";

      try {
        this.snapshot = await fetchRuntimeHealth();
        this.status = "online";
      } catch (error) {
        this.snapshot = null;
        this.status = "offline";
        this.error = error instanceof Error ? error.message : "Runtime 健康检查失败。";
      }
    }
  }
});
