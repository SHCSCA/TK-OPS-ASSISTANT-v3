import { defineStore } from "pinia";

import {
  deleteSubtitleTrack,
  fetchScriptDocument,
  fetchSubtitleTrack,
  fetchSubtitleTracks,
  generateSubtitleTrack,
  updateSubtitleTrack
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  SubtitleSegmentDto,
  SubtitleTrackDto,
  SubtitleTrackGenerateResultDto,
  SubtitleStyleDto
} from "@/types/runtime";
import type { TaskEvent, TaskInfo } from "@/types/task-events";

export interface SubtitleParagraph {
  text: string;
}

export type SubtitleAlignmentStatus =
  | "idle"
  | "loading"
  | "aligning"
  | "saving"
  | "empty"
  | "blocked"
  | "ready"
  | "error";

export type SubtitleAlignmentViewState =
  | "loading"
  | "empty"
  | "ready"
  | "error"
  | "blocked";

type SubtitleAlignmentState = {
  activeSegmentIndex: number;
  document: ScriptDocument | null;
  draftSegments: SubtitleSegmentDto[];
  error: RuntimeRequestErrorShape | null;
  generationResult: SubtitleTrackGenerateResultDto | null;
  paragraphs: SubtitleParagraph[];
  projectId: string;
  selectedTrackId: string | null;
  status: SubtitleAlignmentStatus;
  style: SubtitleStyleDto;
  trackDetailsById: Record<string, SubtitleTrackDto>;
  tracks: SubtitleTrackDto[];
  activeTask: TaskInfo | null;
  _taskUnsubscriber: (() => void) | null;
};

export const useSubtitleAlignmentStore = defineStore("subtitle-alignment", {
  state: (): SubtitleAlignmentState => ({
    activeSegmentIndex: 0,
    document: null,
    draftSegments: [],
    error: null,
    generationResult: null,
    paragraphs: [],
    projectId: "",
    selectedTrackId: null,
    status: "idle",
    style: {
      preset: "default",
      fontSize: 24,
      position: "bottom",
      textColor: "#FFFFFF",
      background: "transparent"
    },
    trackDetailsById: {},
    tracks: [],
    activeTask: null,
    _taskUnsubscriber: null
  }),
  getters: {
    activeSegment: (state): SubtitleSegmentDto | null =>
      state.draftSegments[state.activeSegmentIndex] ?? null,
    selectedTrack: (state): SubtitleTrackDto | null =>
      (state.selectedTrackId ? state.trackDetailsById[state.selectedTrackId] : null) ??
      state.tracks.find((track) => track.id === state.selectedTrackId) ??
      null,
    sourceText: (state): string => state.paragraphs.map((paragraph) => paragraph.text).join("\n\n"),
    viewState(): SubtitleAlignmentViewState {
      if (this.status === "loading" || this.status === "aligning" || this.status === "saving") {
        return "loading";
      }
      if (!this.paragraphs.length) {
        return "empty";
      }
      if (this.status === "error") {
        return "error";
      }
      if (this.status === "blocked" || hasBlockingAlignment(this.selectedTrack)) {
        return "blocked";
      }
      return "ready";
    }
  },
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      this.generationResult = null;
      this.activeTask = null;

      try {
        const [document, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchSubtitleTracks(projectId)
        ]);

        this.document = document;
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));
        this.paragraphs = this.extractParagraphs(document.currentVersion?.content ?? "");

        const initialTrackId = tracks[0]?.id ?? null;
        this.selectedTrackId = initialTrackId;
        if (initialTrackId) {
          await this.selectTrack(initialTrackId);
        } else {
          this.resetDraftSegments();
          this.status = this.resolveBaseStatus();
        }

        this.initializeTaskWatch();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    initializeTaskWatch(): void {
      if (this._taskUnsubscriber) {
        this._taskUnsubscriber();
        this._taskUnsubscriber = null;
      }

      const taskBusStore = useTaskBusStore();
      this._taskUnsubscriber = taskBusStore.subscribeToType("task.progress", (event: TaskEvent) => {
        if (
          event.projectId === this.projectId &&
          (event.taskType === "ai_subtitles" || event.taskType === "subtitle_alignment")
        ) {
          this.handleTaskEvent(event);
        }
      });
    },

    handleTaskEvent(event: TaskEvent): void {
      if (event.type === "task.progress" || event.type === "task.started") {
        this.activeTask = {
          id: event.taskId ?? "",
          task_type: event.taskType || "subtitle_alignment",
          project_id: event.projectId ?? this.projectId,
          status: "running",
          progress: event.progressPct ?? 0,
          message: event.message ?? "正在对齐字幕...",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        this.status = "aligning";
        return;
      }

      if (event.type === "task.completed") {
        this.activeTask = null;
        this.status = "ready";
        void this.refreshTracks();
        return;
      }

      if (event.type === "task.failed") {
        this.activeTask = null;
        this.applyInputError(event.errorMessage ?? "字幕对齐失败");
      }
    },

    async refreshTracks(): Promise<void> {
      if (!this.projectId) {
        return;
      }

      try {
        const tracks = await fetchSubtitleTracks(this.projectId);
        this.tracks = tracks;
        this.trackDetailsById = {
          ...this.trackDetailsById,
          ...Object.fromEntries(tracks.map((track) => [track.id, track]))
        };

        const nextTrackId =
          this.selectedTrackId && tracks.some((track) => track.id === this.selectedTrackId)
            ? this.selectedTrackId
            : tracks[0]?.id ?? null;

        if (nextTrackId) {
          await this.selectTrack(nextTrackId);
        } else {
          this.selectedTrackId = null;
          this.resetDraftSegments();
          this.status = this.resolveBaseStatus();
        }
      } catch (error) {
        console.error("Failed to refresh subtitle tracks:", error);
      }
    },

    async generate(): Promise<SubtitleTrackGenerateResultDto | null> {
      if (!this.projectId) {
        this.applyInputError("未选择有效项目。");
        return null;
      }

      const sourceText = this.sourceText.trim();
      if (!sourceText) {
        this.applyInputError("字幕源文本为空，请先在脚本中心生成并采纳脚本。");
        return null;
      }

      this.status = "aligning";
      this.error = null;

      try {
        const result = await generateSubtitleTrack(this.projectId, {
          sourceText,
          language: "zh-CN",
          stylePreset: this.style.preset || "default"
        });

        this.generationResult = result;
        if (result.track) {
          this.trackDetailsById = {
            ...this.trackDetailsById,
            [result.track.id]: result.track
          };
          this.upsertTrack(result.track);
          this.selectedTrackId = result.track.id;
          this.draftSegments = result.track.segments.map((segment) => ({ ...segment }));
          this.style = { ...result.track.style };
          this.activeSegmentIndex = 0;
        }

        this.status =
          result.track?.status === "blocked" || hasBlockingAlignment(result.track)
            ? "blocked"
            : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },

    async selectTrack(trackId: string): Promise<void> {
      this.selectedTrackId = trackId;
      this.status = "loading";
      this.error = null;
      const cachedTrack =
        this.trackDetailsById[trackId] ?? this.tracks.find((track) => track.id === trackId) ?? null;

      try {
        const track = await fetchSubtitleTrack(trackId);
        this.trackDetailsById = {
          ...this.trackDetailsById,
          [trackId]: track
        };
        this.upsertTrack(track);
        this.draftSegments = track.segments.map((segment) => ({ ...segment }));
        this.style = { ...track.style };
        this.activeSegmentIndex = 0;
        this.status = this.resolveBaseStatus();
      } catch (error) {
        if (cachedTrack) {
          this.trackDetailsById = {
            ...this.trackDetailsById,
            [trackId]: cachedTrack
          };
          this.upsertTrack(cachedTrack);
          this.draftSegments = cachedTrack.segments.map((segment) => ({ ...segment }));
          this.style = { ...cachedTrack.style };
          this.activeSegmentIndex = 0;
          this.status = this.resolveBaseStatus();
          return;
        }
        this.applyRuntimeError(error);
      }
    },

    async updateSelectedTrack(): Promise<SubtitleTrackDto | null> {
      if (!this.selectedTrackId) {
        return null;
      }

      this.status = "saving";
      this.error = null;

      try {
        const updated = await updateSubtitleTrack(this.selectedTrackId, {
          segments: this.draftSegments,
          style: this.style
        });

        this.trackDetailsById = {
          ...this.trackDetailsById,
          [this.selectedTrackId]: updated
        };
        this.upsertTrack(updated);
        this.draftSegments = updated.segments.map((segment) => ({ ...segment }));
        this.style = { ...updated.style };
        this.status = "ready";
        return updated;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },

    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) {
        return;
      }

      try {
        await deleteSubtitleTrack(trackId);
        this.tracks = this.tracks.filter((track) => track.id !== trackId);

        const nextTrackDetails = { ...this.trackDetailsById };
        delete nextTrackDetails[trackId];
        this.trackDetailsById = nextTrackDetails;

        if (this.selectedTrackId === trackId) {
          const nextTrackId = this.tracks[0]?.id ?? null;
          if (nextTrackId) {
            await this.selectTrack(nextTrackId);
          } else {
            this.selectedTrackId = null;
            this.resetDraftSegments();
          }
        }

        this.status = this.resolveBaseStatus();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    updateDraftSegment(index: number, patch: Partial<SubtitleSegmentDto>): void {
      if (this.draftSegments[index]) {
        this.draftSegments[index] = { ...this.draftSegments[index], ...patch };
      }
    },

    updateStyle(patch: Partial<SubtitleStyleDto>): void {
      this.style = { ...this.style, ...patch };
    },

    selectSegment(index: number): void {
      this.activeSegmentIndex = index;
    },

    upsertTrack(track: SubtitleTrackDto): void {
      const currentIndex = this.tracks.findIndex((item) => item.id === track.id);
      if (currentIndex >= 0) {
        this.tracks[currentIndex] = track;
        return;
      }
      this.tracks = [track, ...this.tracks];
    },

    extractParagraphs(content: string): SubtitleParagraph[] {
      return content
        .split(/\n\s*\n/)
        .map((paragraph) => paragraph.trim())
        .filter((paragraph) => paragraph.length > 0)
        .map((text) => ({ text }));
    },

    resetDraftSegments(): void {
      this.draftSegments = [];
      this.activeSegmentIndex = 0;
    },

    resolveBaseStatus(): "empty" | "ready" {
      return this.paragraphs.length > 0 ? "ready" : "empty";
    },

    applyInputError(message: string): void {
      this.status = "error";
      this.error = {
        details: null,
        message,
        requestId: "",
        status: 0
      };
    },

    applyRuntimeError(error: unknown): void {
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "字幕对齐中心请求失败");
    }
  }
});

function hasBlockingAlignment(track: SubtitleTrackDto | null): boolean {
  if (!track) {
    return false;
  }

  return (
    track.status === "blocked" ||
    track.alignment.status === "draft" ||
    track.alignment.status === "needs_alignment" ||
    Boolean(track.alignment.errorCode)
  );
}
