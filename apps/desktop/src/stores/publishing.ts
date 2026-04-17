import { defineStore } from "pinia";
import {
  cancelPublishPlan,
  createPublishPlan,
  deletePublishPlan,
  fetchPublishPlans,
  runPublishingPrecheck,
  submitPublishPlan,
  updatePublishPlan
} from "@/app/runtime-client";
import type {
  PrecheckResultDto,
  PublishPlanCreateInput,
  PublishPlanDto,
  PublishPlanUpdateInput,
  SubmitPlanResultDto
} from "@/types/runtime";
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "发布计划操作失败，请稍后重试。");
}

export const usePublishingStore = defineStore("publishing", {
  state: () => ({
    plans: [] as PublishPlanDto[],
    precheckResult: null as PrecheckResultDto | null,
    submitResult: null as SubmitPlanResultDto | null,
    loading: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    workflowState: "idle" as "idle" | "checking" | "submitting" | "blocked" | "ready" | "error",
    error: null as string | null
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.plans.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    async loadPlans(status?: string) {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.plans = await fetchPublishPlans(status);
        this.status = resolveCollectionStatus(this.plans.length);
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async addPlan(input: PublishPlanCreateInput) {
      this.error = null;
      try {
        const plan = await createPublishPlan(input);
        this.plans.unshift(plan);
        this.status = "ready";
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async updatePlan(id: string, input: PublishPlanUpdateInput) {
      this.error = null;
      try {
        const plan = await updatePublishPlan(id, input);
        this.plans = this.plans.map((item) => (item.id === id ? plan : item));
        this.status = "ready";
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async removePlan(id: string) {
      this.error = null;
      try {
        await deletePublishPlan(id);
        this.plans = this.plans.filter((plan) => plan.id !== id);
        this.status = this.plans.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.error = getErrorMessage(error);
      }
    },
    async precheck(id: string) {
      this.error = null;
      this.workflowState = "checking";
      try {
        this.precheckResult = await runPublishingPrecheck(id);
        await this.loadPlans();
        this.workflowState = this.precheckResult.has_errors ? "blocked" : "ready";
        return this.precheckResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.workflowState = "error";
        return null;
      }
    },
    async submit(id: string) {
      this.error = null;
      this.workflowState = "submitting";
      try {
        this.submitResult = await submitPublishPlan(id);
        await this.loadPlans();
        this.workflowState = "ready";
        return this.submitResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.workflowState = "error";
        return null;
      }
    },
    async cancel(id: string) {
      this.error = null;
      try {
        const plan = await cancelPublishPlan(id);
        this.plans = this.plans.map((item) => (item.id === id ? plan : item));
        this.workflowState = "ready";
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.workflowState = "error";
        return null;
      }
    }
  }
});
