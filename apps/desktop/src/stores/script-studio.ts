import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  fetchScriptDocument,
  generateScriptDocument,
  rewriteScriptDocument,
  saveScriptDocument,
  restoreScriptVersion
} from "@/app/runtime-client";
import { useProjectStore } from "./project";
import type { RuntimeRequestErrorShape, ScriptDocument } from "@/types/runtime";

export type ScriptStudioStatus = "idle" | "loading" | "saving" | "generating" | "ready" | "error";

type ScriptStudioState = {
  document: ScriptDocument | null;
  error: RuntimeRequestErrorShape | null;
  projectId: string;
  status: ScriptStudioStatus;
};

export const useScriptStudioStore = defineStore("script-studio", {
  state: (): ScriptStudioState => ({
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
        this.document = await fetchScriptDocument(projectId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async save(content: string): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "saving";
      this.error = null;

      try {
        this.document = await saveScriptDocument(this.projectId, content);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async generate(topic: string): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "generating";
      this.error = null;

      try {
        this.document = await generateScriptDocument(this.projectId, topic);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async rewrite(instructions: string): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "generating";
      this.error = null;

      try {
        this.document = await rewriteScriptDocument(this.projectId, instructions);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async adoptVersion(revision: number): Promise<void> {
      if (!this.projectId) {
        return;
      }

      this.status = "saving";
      this.error = null;

      try {
        // Use restoreScriptVersion as the adoption mechanism
        this.document = await restoreScriptVersion(this.projectId, String(revision));
        this.status = "ready";
        
        // Update project store to reflect new script revision if needed
        const projectStore = useProjectStore();
        if (projectStore.currentProject?.projectId === this.projectId) {
          await projectStore.load(this.projectId);
        }
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("Script request failed.");

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
