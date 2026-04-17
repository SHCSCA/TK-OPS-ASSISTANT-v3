import { defineStore } from "pinia";

import {
  deleteVoiceTrack,
  fetchScriptDocument,
  fetchVoiceTrack,
  fetchVoiceProfiles,
  fetchVoiceTracks,
  generateVoiceTrack
} from "@/app/runtime-client";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  VoiceProfileDto,
  VoiceTrackDto,
  VoiceTrackGenerateResultDto
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";

export interface VoiceConfig {
  speed: number;
  pitch: number;
  emotion: string;
}

export interface Paragraph {
  text: string;
  estimatedDuration: number;
}

export type VoiceStudioStatus =
  | "idle"
  | "loading"
  | "generating"
  | "empty"
  | "ready"
  | "blocked"
  | "error";

export type VoiceStudioViewState =
  | "loading"
  | "empty"
  | "ready"
  | "error"
  | "blocked"
  | "disabled";

type VoiceStudioState = {
  activeParagraphIndex: number;
  config: VoiceConfig;
  document: ScriptDocument | null;
  error: RuntimeRequestErrorShape | null;
  generationResult: VoiceTrackGenerateResultDto | null;
  paragraphs: Paragraph[];
  profiles: VoiceProfileDto[];
  projectId: string;
  selectedProfileId: string | null;
  selectedTrackId: string | null;
  status: VoiceStudioStatus;
  trackDetailsById: Record<string, VoiceTrackDto>;
  tracks: VoiceTrackDto[];
};

export const useVoiceStudioStore = defineStore("voice-studio", {
  state: (): VoiceStudioState => ({
    activeParagraphIndex: 0,
    config: {
      emotion: "calm",
      pitch: 0,
      speed: 1.0
    },
    document: null,
    error: null,
    generationResult: null,
    paragraphs: [],
    profiles: [],
    projectId: "",
    selectedProfileId: null,
    selectedTrackId: null,
    status: "idle",
    trackDetailsById: {},
    tracks: []
  }),
  getters: {
    hasEnabledProfiles: (state): boolean => state.profiles.some((profile) => profile.enabled),
    hasScriptContent: (state): boolean => state.paragraphs.length > 0,
    selectedProfile: (state): VoiceProfileDto | null =>
      state.profiles.find((profile) => profile.id === state.selectedProfileId) ?? null,
    selectedTrack: (state): VoiceTrackDto | null =>
      (state.selectedTrackId ? state.trackDetailsById[state.selectedTrackId] : null) ??
      state.tracks.find((track) => track.id === state.selectedTrackId) ??
      null,
    sourceText: (state): string => state.paragraphs.map((paragraph) => paragraph.text).join("\n"),
    viewState(): VoiceStudioViewState {
      if (this.status === "loading" || this.status === "generating") {
        return "loading";
      }
      if (!this.hasScriptContent) {
        return "empty";
      }
      if (!this.hasEnabledProfiles) {
        return "disabled";
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
        const [doc, profiles, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchVoiceProfiles(),
          fetchVoiceTracks(projectId)
        ]);
        this.document = doc;
        this.profiles = profiles;
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));
        this.paragraphs = this.extractParagraphs(doc.currentVersion?.content ?? "");
        this.activeParagraphIndex = 0;
        this.selectedProfileId = this.resolveProfileSelection(profiles);
        this.selectedTrackId = tracks[0]?.id ?? null;
        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }
        this.status = this.resolveStatus();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async generate(): Promise<VoiceTrackGenerateResultDto | null> {
      if (!this.projectId) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      const sourceText = this.sourceText.trim();
      if (!sourceText) {
        this.applyInputError("脚本文本为空，请先在脚本与选题中心创建内容。");
        return null;
      }

      if (!this.selectedProfileId) {
        this.applyInputError("当前没有可用音色，请先检查 AI 与系统设置。");
        return null;
      }

      this.status = "generating";
      this.error = null;
      try {
        const result = await generateVoiceTrack(this.projectId, {
          emotion: this.config.emotion,
          pitch: this.config.pitch,
          profileId: this.selectedProfileId,
          sourceText,
          speed: this.config.speed
        });
        this.generationResult = result;
        this.upsertTrack(result.track);
        this.trackDetailsById = {
          ...this.trackDetailsById,
          [result.track.id]: result.track
        };
        this.selectedTrackId = result.track.id;
        this.status = result.track.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    extractParagraphs(content: string): Paragraph[] {
      return content
        .split("\n")
        .map((paragraph) => paragraph.trim())
        .filter((paragraph) => paragraph.length > 0)
        .map((text) => ({
          text,
          estimatedDuration: Math.round(text.length * 0.4 * 10) / 10
        }));
    },
    selectProfile(profileId: string): void {
      this.selectedProfileId = profileId;
      this.status = this.resolveStatus();
    },
    async selectTrack(trackId: string): Promise<void> {
      this.selectedTrackId = trackId;
      await this.loadTrackDetail(trackId, true);
      if (this.error) {
        return;
      }
      this.status = this.resolveStatus();
    },
    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) return;
      this.error = null;

      try {
        await deleteVoiceTrack(trackId);
        this.tracks = await fetchVoiceTracks(this.projectId);
        delete this.trackDetailsById[trackId];
        this.selectedTrackId = this.tracks[0]?.id ?? null;
        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }
        this.status = this.resolveStatus();
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    resolveProfileSelection(profiles: VoiceProfileDto[]): string | null {
      if (this.selectedProfileId && profiles.some((profile) => profile.id === this.selectedProfileId)) {
        return this.selectedProfileId;
      }
      return profiles.find((profile) => profile.enabled)?.id ?? null;
    },
    upsertTrack(track: VoiceTrackDto): void {
      this.tracks = [track, ...this.tracks.filter((item) => item.id !== track.id)];
    },
    async loadTrackDetail(trackId: string, surfaceError: boolean): Promise<void> {
      try {
        const detail = await fetchVoiceTrack(trackId);
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
    resolveStatus(): VoiceStudioStatus {
      if (!this.paragraphs.length) {
        return "empty";
      }
      return "ready";
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
      this.error = toRuntimeErrorShape(error, "配音服务请求失败，请稍后重试。");
    }
  }
});
