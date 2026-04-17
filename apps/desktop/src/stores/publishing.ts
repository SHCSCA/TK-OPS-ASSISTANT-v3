import { defineStore } from "pinia";
import {
  cancelPublishPlan,
  createPublishPlan,
  deletePublishPlan,
  fetchPublishPlans,
  fetchPublishReceipt,
  runPublishingPrecheck,
  submitPublishPlan,
  updatePublishPlan
} from "@/app/runtime-client";
import type {
  PrecheckResultDto,
  PublishPlanCreateInput,
  PublishPlanDto,
  PublishPlanUpdateInput,
  PublishReceiptDto,
  SubmitPlanResultDto
} from "@/types/runtime";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "发布计划操作失败";
}

export const usePublishingStore = defineStore("publishing", {
  state: () => ({
    plans: [] as PublishPlanDto[],
    receiptsByPlanId: {} as Record<string, PublishReceiptDto>,
    precheckResult: null as PrecheckResultDto | null,
    submitResult: null as SubmitPlanResultDto | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadPlans(status?: string) {
      this.loading = true;
      this.error = null;
      try {
        this.plans = await fetchPublishPlans(status);
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load publish plans", error);
      } finally {
        this.loading = false;
      }
    },
    async addPlan(input: PublishPlanCreateInput) {
      this.error = null;
      try {
        const plan = await createPublishPlan(input);
        this.plans.unshift(plan);
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to create publish plan", error);
        return null;
      }
    },
    async updatePlan(id: string, input: PublishPlanUpdateInput) {
      this.error = null;
      try {
        const plan = await updatePublishPlan(id, input);
        this.plans = this.plans.map((item) => (item.id === id ? plan : item));
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update publish plan", error);
        return null;
      }
    },
    async removePlan(id: string) {
      this.error = null;
      try {
        await deletePublishPlan(id);
        this.plans = this.plans.filter((plan) => plan.id !== id);
        delete this.receiptsByPlanId[id];
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to delete publish plan", error);
      }
    },
    async precheck(id: string) {
      this.error = null;
      try {
        this.precheckResult = await runPublishingPrecheck(id);
        await this.loadPlans();
        return this.precheckResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to run publishing precheck", error);
        return null;
      }
    },
    async submit(id: string) {
      this.error = null;
      try {
        this.submitResult = await submitPublishPlan(id);
        await this.loadPlans();
        return this.submitResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to submit publish plan", error);
        return null;
      }
    },
    async cancel(id: string) {
      this.error = null;
      try {
        const plan = await cancelPublishPlan(id);
        this.plans = this.plans.map((item) => (item.id === id ? plan : item));
        return plan;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to cancel publish plan", error);
        return null;
      }
    },
    async loadReceipt(id: string) {
      this.error = null;
      try {
        const receipt = await fetchPublishReceipt(id);
        this.receiptsByPlanId[id] = receipt;
        return receipt;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load publish receipt", error);
        return null;
      }
    }
  }
});
