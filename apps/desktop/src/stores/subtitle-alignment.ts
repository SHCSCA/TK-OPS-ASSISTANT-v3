import { defineStore } from "pinia";

import {
  deleteSubtitleTrack,
  fetchScriptDocument,
  fetchSubtitleTrack,
  fetchSubtitleTracks,
  generateSubtitleTrack,
  updateSubtitleTrack
} from "@/app/runtime-client";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  SubtitleSegmentDto,
  SubtitleStyleDto,
  SubtitleTrackDto,
  SubtitleTrackGenerateResultDto
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export interface SubtitleParagraph {
  text: string;
}

export type SubtitleAlignmentStatus =
  | "idle"
  | "loading"
  | "empty"
  | "ready"
  | "aligning"
  | "blocked"
  | "saving"
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
};

const DEFAULT_STYLE: SubtitleStyleDto = {
  preset: "creator-default",
  fontSize: 32,
  position: "bottom",
  textColor: "#FFFFFF",
  background: "rgba(0,0,0,0.62)"
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
    style: { ...DEFAULT_STYLE },
    trackDetailsById: {},
    tracks: []
  }),
  getters: {
    selectedTrack: (state): SubtitleTrackDto | null =>
      (state.selectedTrackId ? state.trackDetailsById[state.selectedTrackId] : null) ??
      state.tracks.find((track) => track.id === state.selectedTrackId) ??
      null,
    activeSegment: (state): SubtitleSegmentDto | null =>
      state.draftSegments[state.activeSegmentIndex] ?? null,
    sourceText: (state): string => state.paragraphs.map((paragraph) => paragraph.text).join("\n"),
    viewState(): SubtitleAlignmentViewState {
      if (
        this.status === "loading" ||
        this.status === "aligning" ||
        this.status === "saving"
      ) {
        return "loading";
      }
      if (!this.paragraphs.length) {
        return "empty";
      }
      if (this.status === "error") {
        return "error";
      }
      if (this.status === "blocked" || this.selectedTrack?.status === "blocked") {
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
      try {
        const [doc, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchSubtitleTracks(projectId)
        ]);
        this.document = doc;
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));
        this.paragraphs = this.extractParagraphs(doc.currentVersion?.content ?? "");
        this.selectedTrackId = tracks[0]?.id ?? null;
        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }
        this.syncDraftFromSelectedTrack();
        this.status = this.paragraphs.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async generate(): Promise<SubtitleTrackGenerateResultDto | null> {
      if (!this.projectId) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      const sourceText = this.sourceText.trim();
      if (!sourceText) {
        this.applyInputError("字幕源文本为空，请先在脚本与选题中心创建内容。");
        return null;
      }

      this.status = "aligning";
      this.error = null;
      try {
        const result = await generateSubtitleTrack(this.projectId, {
          sourceText,
          language: "zh-CN",
          stylePreset: this.style.preset
        });
        this.generationResult = result;
        this.upsertTrack(result.track);
        this.trackDetailsById = {
          ...this.trackDetailsById,
          [result.track.id]: result.track
        };
        this.selectedTrackId = result.track.id;
        this.syncDraftFromSelectedTrack();
        this.status = result.track.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async selectTrack(trackId: string): Promise<void> {
      this.selectedTrackId = trackId;
      await this.loadTrackDetail(trackId, true);
      if (this.error) {
        return;
      }
      this.syncDraftFromSelectedTrack();
    },
    selectSegment(index: number): void {
      this.activeSegmentIndex = Math.max(0, Math.min(index, this.draftSegments.length - 1));
    },
    updateDraftSegment(index: number, patch: Partial<SubtitleSegmentDto>): void {
      const segment = this.draftSegments[index];
      if (!segment) return;
      this.draftSegments[index] = { ...segment, ...patch };
    },
    updateStyle(patch: Partial<SubtitleStyleDto>): void {
      this.style = { ...this.style, ...patch };
    },
    async updateSelectedTrack(): Promise<SubtitleTrackDto | null> {
      if (!this.selectedTrackId) {
        this.applyInputError("请先选择字幕版本。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      try {
        const updated = await updateSubtitleTrack(this.selectedTrackId, {
          segments: this.draftSegments,
          style: this.style
        });
        this.upsertTrack(updated);
        this.trackDetailsById = {
          ...this.trackDetailsById,
          [updated.id]: updated
        };
        this.selectedTrackId = updated.id;
        this.syncDraftFromSelectedTrack();
        this.status = "ready";
        return updated;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) return;
      this.error = null;

      try {
        await deleteSubtitleTrack(trackId);
        this.tracks = await fetchSubtitleTracks(this.projectId);
        delete this.trackDetailsById[trackId];
        this.selectedTrackId = this.tracks[0]?.id ?? null;
        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }
        this.syncDraftFromSelectedTrack();
        this.status = this.paragraphs.length > 0 ? "ready" : "empty";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    extractParagraphs(content: string): SubtitleParagraph[] {
      return content
        .split("\n")
        .map((paragraph) => paragraph.trim())
        .filter((paragraph) => paragraph.length > 0)
        .map((text) => ({ text }));
    },
    upsertTrack(track: SubtitleTrackDto): void {
      this.tracks = [track, ...this.tracks.filter((item) => item.id !== track.id)];
    },
    async loadTrackDetail(trackId: string, surfaceError: boolean): Promise<void> {
      try {
        const detail = await fetchSubtitleTrack(trackId);
        this.trackDetailsById = {
          ...this.trackDetailsById,
          [trackId]: detail
        };
        this.upsertTrack(detail);
      } catch (error) {
        if (surfaceError) {
          this.applyRuntimeError(error);
        }
      }
    },
    syncDraftFromSelectedTrack(): void {
      const track = this.selectedTrack;
      this.draftSegments = track ? track.segments.map((segment) => ({ ...segment })) : [];
      this.style = track ? { ...track.style } : { ...DEFAULT_STYLE };
      this.activeSegmentIndex = 0;
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
      this.error = toRuntimeErrorShape(error, "字幕对齐服务请求失败，请稍后重试。");
    }
  }
});
