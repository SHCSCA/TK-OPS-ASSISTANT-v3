import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  fetchStoryboardDocument,
  generateStoryboardDocument,
  saveStoryboardDocument,
  syncStoryboardFromScript
} from "@/app/runtime-client";
import type {
  RuntimeRequestErrorShape,
  StoryboardDocument,
  StoryboardScene
} from "@/types/runtime";

export type StoryboardStoreStatus = "idle" | "loading" | "saving" | "generating" | "ready" | "error";

type StoryboardStoreState = {
  document: StoryboardDocument | null;
  error: RuntimeRequestErrorShape | null;
  projectId: string;
  status: StoryboardStoreStatus;
};

export const useStoryboardStore = defineStore("storyboard", {
  state: (): StoryboardStoreState => ({
    document: null,
    error: null,
    projectId: "",
    status: "idle"
  }),
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;

      try {
        this.document = await fetchStoryboardDocument(projectId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async generate(): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "generating";
      this.error = null;

      try {
        this.document = await generateStoryboardDocument(this.projectId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async syncFromScript(): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "generating"; // Re-use generating status for sync UI feedback
      this.error = null;

      try {
        this.document = await syncStoryboardFromScript(this.projectId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async save(
      basedOnScriptRevision: number,
      scenes: StoryboardScene[],
      markdown?: string | null,
      storyboardJson?: Record<string, unknown> | null
    ): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "saving";
      this.error = null;

      try {
        this.document = await saveStoryboardDocument(
          this.projectId,
          basedOnScriptRevision,
          scenes,
          markdown,
          storyboardJson
        );
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("Storyboard request failed.");

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
