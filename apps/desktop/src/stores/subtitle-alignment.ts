import { defineStore } from "pinia";

import { RuntimeRequestError } from "@/app/runtime-client";
import type { RuntimeRequestErrorShape } from "@/types/runtime";

export interface SubtitleEntry {
  id: string;
  startMs: number;
  endMs: number;
  text: string;
  selected: boolean;
}

export type SubtitleAlignmentStatus = "idle" | "aligning" | "ready" | "error";

type SubtitleAlignmentState = {
  error: RuntimeRequestErrorShape | null;
  projectId: string;
  status: SubtitleAlignmentStatus;
  subtitles: SubtitleEntry[];
  videoId: string;
};

export const useSubtitleAlignmentStore = defineStore("subtitle-alignment", {
  state: (): SubtitleAlignmentState => ({
    error: null,
    projectId: "",
    status: "idle",
    subtitles: [],
    videoId: ""
  }),
  actions: {
    async align(): Promise<void> {
      if (!this.videoId) return;
      this.status = "aligning";
      this.error = null;
      try {
        // V1: POST /api/subtitles/videos/{id}/align → pending_provider
        await new Promise<void>((resolve) => setTimeout(resolve, 1500));
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    addSubtitle(): void {
      const lastEnd = this.subtitles[this.subtitles.length - 1]?.endMs ?? 0;
      this.subtitles.push({
        id: Math.random().toString(36).substring(2),
        startMs: lastEnd,
        endMs: lastEnd + 2000,
        text: "新字幕内容",
        selected: false
      });
    },
    updateSubtitle(index: number, patch: Partial<SubtitleEntry>): void {
      if (this.subtitles[index]) {
        this.subtitles[index] = { ...this.subtitles[index], ...patch };
      }
    },
    selectSubtitle(index: number): void {
      this.subtitles.forEach((s, i) => {
        s.selected = i === index;
      });
    },
    applyRuntimeError(error: unknown): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("字幕对齐请求失败");
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
