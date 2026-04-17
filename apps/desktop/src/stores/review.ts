import { defineStore } from "pinia";
import {
  analyzeReviewProject,
  applyReviewSuggestionToScript,
  fetchReviewSuggestions,
  fetchReviewSummary,
  generateReviewSuggestions,
  updateReviewSuggestion,
  updateReviewSummary
} from "@/app/runtime-client";
import type {
  AnalyzeProjectResultDto,
  ApplyReviewSuggestionResultDto,
  GenerateReviewSuggestionsResultDto,
  ReviewSuggestion,
  ReviewSuggestionUpdateInput,
  ReviewSummaryDto,
  ReviewSummaryUpdateInput
} from "@/types/runtime";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "复盘数据操作失败";
}

export const useReviewStore = defineStore("review", {
  state: () => ({
    currentProjectId: null as string | null,
    summary: null as ReviewSummaryDto | null,
    suggestions: [] as ReviewSuggestion[],
    lastAnalyzeResult: null as AnalyzeProjectResultDto | null,
    lastGenerateSuggestionsResult: null as GenerateReviewSuggestionsResultDto | null,
    lastApplySuggestionResult: null as ApplyReviewSuggestionResultDto | null,
    loading: false,
    analyzing: false,
    error: null as string | null
  }),
  actions: {
    async loadSummary(projectId: string) {
      this.loading = true;
      this.error = null;
      this.currentProjectId = projectId;
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
      this.currentProjectId = projectId;
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
      this.currentProjectId = projectId;
      try {
        this.summary = await updateReviewSummary(projectId, input);
        return this.summary;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update review summary", error);
        return null;
      }
    },
    async loadSuggestions(projectId: string) {
      this.error = null;
      this.currentProjectId = projectId;
      try {
        this.suggestions = await fetchReviewSuggestions(projectId);
        return this.suggestions;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to load review suggestions", error);
        return [];
      }
    },
    async generateSuggestions(projectId: string) {
      this.error = null;
      this.currentProjectId = projectId;
      try {
        this.lastGenerateSuggestionsResult = await generateReviewSuggestions(projectId);
        await this.loadSuggestions(projectId);
        return this.lastGenerateSuggestionsResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to generate review suggestions", error);
        return null;
      }
    },
    async updateSuggestion(suggestionId: string, input: ReviewSuggestionUpdateInput) {
      this.error = null;
      try {
        const suggestion = await updateReviewSuggestion(suggestionId, input);
        this.suggestions = this.suggestions.map((item) =>
          item.id === suggestionId ? suggestion : item
        );
        return suggestion;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to update review suggestion", error);
        return null;
      }
    },
    async applySuggestionToScript(suggestionId: string) {
      this.error = null;
      try {
        this.lastApplySuggestionResult = await applyReviewSuggestionToScript(suggestionId);
        this.suggestions = this.suggestions.map((item) =>
          item.id === suggestionId ? { ...item, status: "applied" } : item
        );
        if (this.currentProjectId) {
          await this.loadSummary(this.currentProjectId);
        }
        return this.lastApplySuggestionResult;
      } catch (error) {
        this.error = getErrorMessage(error);
        console.error("Failed to apply review suggestion", error);
        return null;
      }
    }
  }
});
