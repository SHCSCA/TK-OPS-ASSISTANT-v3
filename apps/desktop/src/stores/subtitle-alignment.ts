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
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  SubtitleSegmentDto,
  SubtitleStyleConfig,
  SubtitleTrackDto,
  SubtitleTrackGenerateResultDto
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";
import type { TaskEvent, TaskInfo } from "@/types/task-events";

export type SubtitleAlignmentStatus =
  | "idle"
  | "loading"
  | "aligning"
  | "saving"
  | "ready"
  | "error";

type SubtitleAlignmentState = {
  activeSegmentIndex: number;
  document: ScriptDocument | null;
  draftSegments: SubtitleSegmentDto[];
  error: RuntimeRequestErrorShape | null;
  generationResult: SubtitleTrackGenerateResultDto | null;
  paragraphs: string[];
  projectId: string;
  selectedTrackId: string | null;
  status: SubtitleAlignmentStatus;
  style: SubtitleStyleConfig;
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
      fontSize: 24,
      color: "#FFFFFF",
      strokeColor: "#000000",
      strokeWidth: 2,
      backgroundColor: "transparent",
      position: "bottom",
      offsetY: 20
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
      null
  },
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      this.generationResult = null;
      this.activeTask = null;

      try {
        const [doc, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchSubtitleTracks(projectId)
        ]);
        this.document = doc;
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));
        this.paragraphs = (doc.currentVersion?.content ?? "")
          .split("\n")
          .map((p) => p.trim())
          .filter(Boolean);

        const initialTrackId = tracks[0]?.id ?? null;
        if (initialTrackId) {
          await this.selectTrack(initialTrackId);
        } else {
          this.draftSegments = [];
          this.activeSegmentIndex = 0;
        }
        
        this.status = "ready";
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
      this._taskUnsubscriber = taskBusStore.subscribeToType("ai-subtitles", (event: TaskEvent) => {
        if (event.projectId === this.projectId) {
          this.handleTaskEvent(event);
        }
      });
    },

    handleTaskEvent(event: TaskEvent): void {
      if (event.type === "task.progress" || event.type === "task.started") {
        this.activeTask = {
          id: event.taskId ?? "",
          status: "running",
          progress: event.progressPct ?? 0,
          message: event.message ?? "正在对齐字幕...",
          task_type: "ai-subtitles",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        } as any;
        this.status = "aligning";
      } else if (event.type === "task.completed") {
        this.activeTask = null;
        this.status = "ready";
        void this.refreshTracks();
      } else if (event.type === "task.failed") {
        this.activeTask = null;
        this.status = "error";
        this.applyInputError(event.errorMessage ?? "字幕对齐失败");
      }
    },

    async refreshTracks(): Promise<void> {
      if (!this.projectId) return;
      try {
        const tracks = await fetchSubtitleTracks(this.projectId);
        this.tracks = tracks;
        if (tracks.length > 0) {
          await this.selectTrack(tracks[0].id);
        }
      } catch (e) {
        console.error("Failed to refresh subtitle tracks:", e);
      }
    },

    async generate(): Promise<SubtitleTrackGenerateResultDto | null> {
      if (!this.projectId) return null;
      this.status = "aligning";
      this.error = null;
      try {
        const result = await generateSubtitleTrack(this.projectId);
        this.generationResult = result;
        if (result.track) {
          this.upsertTrack(result.track);
          this.selectedTrackId = result.track.id;
          this.draftSegments = result.track.segments.map((s) => ({ ...s }));
          this.style = { ...result.track.style };
        }
        this.status = "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },

    async selectTrack(trackId: string): Promise<void> {
      this.selectedTrackId = trackId;
      this.status = "loading";
      try {
        const track = await fetchSubtitleTrack(trackId);
        this.trackDetailsById[trackId] = track;
        this.upsertTrack(track);
        this.draftSegments = track.segments.map((s) => ({ ...s }));
        this.style = { ...track.style };
        this.activeSegmentIndex = 0;
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async updateSelectedTrack(): Promise<void> {
      if (!this.selectedTrackId) return;
      this.status = "saving";
      try {
        const updated = await updateSubtitleTrack(this.selectedTrackId, {
          segments: this.draftSegments,
          style: this.style
        });
        this.trackDetailsById[this.selectedTrackId] = updated;
        this.upsertTrack(updated);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) return;
      try {
        await deleteSubtitleTrack(trackId);
        this.tracks = this.tracks.filter((t) => t.id !== trackId);
        delete this.trackDetailsById[trackId];
        if (this.selectedTrackId === trackId) {
          const next = this.tracks[0]?.id ?? null;
          if (next) await this.selectTrack(next);
          else {
            this.selectedTrackId = null;
            this.draftSegments = [];
          }
        }
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    updateDraftSegment(index: number, patch: Partial<SubtitleSegmentDto>): void {
      if (this.draftSegments[index]) {
        this.draftSegments[index] = { ...this.draftSegments[index], ...patch };
      }
    },

    updateStyle(patch: Partial<SubtitleStyleConfig>): void {
      this.style = { ...this.style, ...patch };
    },

    selectSegment(index: number): void {
      this.activeSegmentIndex = index;
    },

    upsertTrack(track: SubtitleTrackDto): void {
      const idx = this.tracks.findIndex((t) => t.id === track.id);
      if (idx >= 0) this.tracks[idx] = track;
      else this.tracks = [track, ...this.tracks];
    },

    applyInputError(message: string): void {
      this.status = "error";
      this.error = { details: null, message, requestId: "", status: 0 };
    },

    applyRuntimeError(error: unknown): void {
      this.status = "error";
      this.error = toRuntimeErrorShape(error, "字幕对齐中心请求失败");
    }
  }
});
