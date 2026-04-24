import { defineStore } from "pinia";
import {
  cancelPublishPlan,
  createPublishPlan,
  deletePublishPlan,
  fetchPublishingCalendar,
  fetchPublishPlans,
  fetchPublishReceipt,
  fetchPublishReceipts,
  runPublishingPrecheck,
  submitPublishPlan,
  updatePublishPlan
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  PrecheckResultDto,
  PublishCalendarDto,
  PublishPlanCreateInput,
  PublishPlanDto,
  PublishReceiptDto,
  PublishPlanUpdateInput,
  SubmitPlanResultDto
} from "@/types/runtime";
import type { TaskEvent } from "@/types/task-events";
import { resolveCollectionStatus, toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "发布计划操作失败，请稍后重试。");
}

export const usePublishingStore = defineStore("publishing", {
  state: () => ({
    plans: [] as PublishPlanDto[],
    calendar: null as PublishCalendarDto | null,
    latestReceipt: null as PublishReceiptDto | null,
    receiptsByPlanId: {} as Record<string, PublishReceiptDto[]>,
    precheckResult: null as PrecheckResultDto | null,
    submitResult: null as SubmitPlanResultDto | null,
    loading: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    workflowState: "idle" as "idle" | "checking" | "submitting" | "blocked" | "ready" | "error",
    error: null as string | null,
    _unsubscribers: {} as Record<string, () => void>
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.status === "loading") return "loading";
      if (state.status === "error") return "error";
      return state.plans.length > 0 ? "ready" : "empty";
    }
  },
  actions: {
    initializeWebSocket(): void {
      useTaskBusStore().connect();
    },
    syncSubscriptions(): void {
      const taskBus = useTaskBusStore();
      this.plans.forEach((plan) => {
        const isUnfinished = plan.status === "submitting" || plan.status === "ready";
        if (isUnfinished && !this._unsubscribers[plan.id]) {
          this._unsubscribers[plan.id] = taskBus.subscribe(plan.id, (event: TaskEvent) => {
            if (event.type === "task.completed" || event.type === "task.failed") {
              void this.loadPlans();
            }
          });
        }
      });
    },
    async loadPlans(status?: string) {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.plans = await fetchPublishPlans(status);
        this.status = resolveCollectionStatus(this.plans.length);
        this.syncSubscriptions();
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
        this.syncSubscriptions();
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
        if (this._unsubscribers[id]) {
          this._unsubscribers[id]();
          delete this._unsubscribers[id];
        }
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
        this.latestReceipt = null;
        await this.loadPlans();
        if (this.submitResult.receipt) {
          this.latestReceipt = {
            ...this.submitResult.receipt,
            plan_id: this.submitResult.plan_id,
            platform_response_json: null,
            created_at: this.submitResult.submitted_at
          };
        }
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
    },
    async loadCalendar() {
      this.error = null;
      try {
        this.calendar = await fetchPublishingCalendar();
        return this.calendar;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async loadLatestReceipt(id: string) {
      this.error = null;
      try {
        this.latestReceipt = await fetchPublishReceipt(id);
        return this.latestReceipt;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      }
    },
    async loadReceipts(id: string) {
      this.error = null;
      try {
        const receipts = await fetchPublishReceipts(id);
        this.receiptsByPlanId[id] = receipts;
        return receipts;
      } catch (error) {
        this.error = getErrorMessage(error);
        return [];
      }
    }
  }
});
