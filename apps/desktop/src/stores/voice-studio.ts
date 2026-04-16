import { defineStore } from "pinia";

import { RuntimeRequestError } from "@/app/runtime-client";
import { fetchScriptDocument } from "@/app/runtime-client";
import type { RuntimeRequestErrorShape, ScriptDocument } from "@/types/runtime";

export interface VoiceConfig {
  speakerId: string;
  speed: number;     // 0.5–2.0
  pitch: number;     // -50 ~ +50
  emotion: string;   // calm / happy / news / tender
}

export interface Paragraph {
  text: string;
  estimatedDuration: number; // seconds
}

export type VoiceStudioStatus = "idle" | "loading" | "generating" | "ready" | "error";

type VoiceStudioState = {
  activeParagraphIndex: number;
  config: VoiceConfig;
  document: ScriptDocument | null;
  error: RuntimeRequestErrorShape | null;
  paragraphs: Paragraph[];
  projectId: string;
  status: VoiceStudioStatus;
};

export const useVoiceStudioStore = defineStore("voice-studio", {
  state: (): VoiceStudioState => ({
    activeParagraphIndex: 0,
    config: {
      emotion: "calm",
      pitch: 0,
      speakerId: "xiaoxiao",
      speed: 1.0
    },
    document: null,
    error: null,
    paragraphs: [],
    projectId: "",
    status: "idle"
  }),
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      try {
        const doc = await fetchScriptDocument(projectId);
        this.document = doc;
        const content = doc.currentVersion?.content ?? "";
        this.paragraphs = content
          .split("\n")
          .map((p) => p.trim())
          .filter((p) => p.length > 0)
          .map((text) => ({
            text,
            estimatedDuration: Math.round(text.length * 0.4 * 10) / 10
          }));
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async generate(): Promise<void> {
      if (!this.projectId) return;
      this.status = "generating";
      this.error = null;
      try {
        // V1: POST /api/voice/jobs returns pending_provider – simulate delay
        await new Promise<void>((resolve) => setTimeout(resolve, 1500));
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    applyRuntimeError(error: unknown): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("配音服务请求失败");
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
