import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  deleteVoiceTrack,
  fetchScriptDocument,
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
  | "ready"
  | "blocked"
  | "error";

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
    tracks: []
  }),
  getters: {
    selectedProfile: (state): VoiceProfileDto | null =>
      state.profiles.find((profile) => profile.id === state.selectedProfileId) ?? null,
    selectedTrack: (state): VoiceTrackDto | null =>
      state.tracks.find((track) => track.id === state.selectedTrackId) ?? null,
    sourceText: (state): string => state.paragraphs.map((paragraph) => paragraph.text).join("\n")
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
        const content = doc.currentVersion?.content ?? "";
        this.paragraphs = content
          .split("\n")
          .map((p) => p.trim())
          .filter((p) => p.length > 0)
          .map((text) => ({
            text,
            estimatedDuration: Math.round(text.length * 0.4 * 10) / 10
          }));
        this.activeParagraphIndex = 0;
        this.selectedProfileId = this.resolveProfileSelection(profiles);
        this.selectedTrackId = tracks[0]?.id ?? null;
        this.status = "ready";
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
        this.selectedTrackId = result.track.id;
        this.status = result.track.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    selectProfile(profileId: string): void {
      this.selectedProfileId = profileId;
    },
    selectTrack(trackId: string): void {
      this.selectedTrackId = trackId;
    },
    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) return;
      this.error = null;

      try {
        await deleteVoiceTrack(trackId);
        this.tracks = await fetchVoiceTracks(this.projectId);
        this.selectedTrackId = this.tracks[0]?.id ?? null;
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    resolveProfileSelection(profiles: VoiceProfileDto[]): string | null {
      if (this.selectedProfileId && profiles.some((profile) => profile.id === this.selectedProfileId)) {
        return this.selectedProfileId;
      }
      return profiles.find((profile) => profile.enabled)?.id ?? profiles[0]?.id ?? null;
    },
    upsertTrack(track: VoiceTrackDto): void {
      this.tracks = [track, ...this.tracks.filter((item) => item.id !== track.id)];
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
