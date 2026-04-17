import { defineStore } from "pinia";
import {
  analyzeReviewProject,
  fetchReviewSummary,
  updateReviewSummary
} from "@/app/runtime-client";
import type {
  AnalyzeProjectResultDto,
  ReviewSummaryDto,
  ReviewSummaryUpdateInput
} from "@/types/runtime";
import { toRuntimeErrorMessage } from "@/stores/runtime-store-helpers";

function getErrorMessage(error: unknown): string {
  return toRuntimeErrorMessage(error, "复盘数据操作失败，请稍后重试。");
}

export const useReviewStore = defineStore("review", {
  state: () => ({
    summary: null as ReviewSummaryDto | null,
    lastAnalyzeResult: null as AnalyzeProjectResultDto | null,
    loading: false,
    analyzing: false,
    status: "idle" as "idle" | "loading" | "empty" | "ready" | "error",
    error: null as string | null
  }),
  getters: {
    viewState: (state): "loading" | "empty" | "ready" | "error" => {
      if (state.loading) return "loading";
      if (state.status === "error") return "error";
      return state.summary ? "ready" : "empty";
    }
  },
  actions: {
    async loadSummary(projectId: string) {
      this.loading = true;
      this.status = "loading";
      this.error = null;
      try {
        this.summary = await fetchReviewSummary(projectId);
        this.status = this.summary ? "ready" : "empty";
      } catch (error) {
        this.status = "error";
        this.error = getErrorMessage(error);
      } finally {
        this.loading = false;
      }
    },
    async analyze(projectId: string) {
      this.analyzing = true;
      this.error = null;
      try {
        this.lastAnalyzeResult = await analyzeReviewProject(projectId);
        await this.loadSummary(projectId);
        return this.lastAnalyzeResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        return null;
      } finally {
        this.analyzing = false;
      }
    },
    async updateSummary(projectId: string, input: ReviewSummaryUpdateInput) {
      this.error = null;
      try {
        this.summary = await updateReviewSummary(projectId, input);
        this.status = this.summary ? "ready" : "empty";
        return this.summary;
      } catch (error) {
        this.error = getErrorMessage(error);
        this.status = "error";
        return null;
      }
    }
  }
});
