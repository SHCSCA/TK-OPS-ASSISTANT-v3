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

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "复盘数据操作失败";
}

export const useReviewStore = defineStore("review", {
  state: () => ({
    summary: null as ReviewSummaryDto | null,
    lastAnalyzeResult: null as AnalyzeProjectResultDto | null,
    loading: false,
    analyzing: false,
    error: null as string | null
  }),
  actions: {
    async loadSummary(projectId: string) {
      this.loading = true;
      this.error = null;
      try {
        this.summary = await fetchReviewSummary(projectId);
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load review summary", error);
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
        console.error("Failed to analyze review project", error);
        return null;
      } finally {
        this.analyzing = false;
      }
    },
    async updateSummary(projectId: string, input: ReviewSummaryUpdateInput) {
      this.error = null;
      try {
        this.summary = await updateReviewSummary(projectId, input);
        return this.summary;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update review summary", error);
        return null;
      }
    }
  }
});
