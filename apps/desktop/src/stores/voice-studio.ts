import { defineStore } from "pinia";

import {
  deleteVoiceTrack,
  fetchScriptDocument,
  fetchVoiceProfiles,
  fetchVoiceTrack,
  fetchVoiceTracks,
  generateVoiceTrack,
  refreshVoiceProfiles
} from "@/app/runtime-client";
import { extractScriptDocumentDownstreamText } from "@/modules/scripts/script-document-view-model";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  VoiceProfileDto,
  VoiceProfileRefreshResultDto,
  VoiceTrackDto,
  VoiceTrackGenerateResultDto
} from "@/types/runtime";
import type { TaskEvent, TaskInfo } from "@/types/task-events";

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
  activeTask: TaskInfo | null;
  config: VoiceConfig;
  document: ScriptDocument | null;
  error: RuntimeRequestErrorShape | null;
  generationResult: VoiceTrackGenerateResultDto | null;
  paragraphs: Paragraph[];
  profiles: VoiceProfileDto[];
  profileSyncing: boolean;
  projectId: string;
  selectedProfileId: string | null;
  selectedTrackId: string | null;
  status: VoiceStudioStatus;
  trackDetailsById: Record<string, VoiceTrackDto>;
  tracks: VoiceTrackDto[];
  _taskUnsubscriber: (() => void) | null;
};

export const useVoiceStudioStore = defineStore("voice-studio", {
  state: (): VoiceStudioState => ({
    activeParagraphIndex: 0,
    activeTask: null,
    config: {
      emotion: "calm",
      pitch: 0,
      speed: 1
    },
    document: null,
    error: null,
    generationResult: null,
    paragraphs: [],
    profiles: [],
    profileSyncing: false,
    projectId: "",
    selectedProfileId: null,
    selectedTrackId: null,
    status: "idle",
    trackDetailsById: {},
    tracks: [],
    _taskUnsubscriber: null
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
      this.activeTask = null;
      this.profileSyncing = false;

      try {
        const [document, profiles, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchVoiceProfiles(),
          fetchVoiceTracks(projectId)
        ]);

        this.document = document;
        this.profiles = this.filterSupportedProfiles(profiles);
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));
        this.paragraphs = this.extractParagraphs(
          document.currentVersion?.documentJson ?? null,
          document.currentVersion?.content ?? ""
        );
        this.activeParagraphIndex = 0;
        this.selectedProfileId = this.resolveProfileSelection(this.profiles);
        this.selectedTrackId = tracks[0]?.id ?? null;

        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
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
      const unsubscribers = [
        taskBusStore.subscribeToType("task.started", this.handleTaskEvent),
        taskBusStore.subscribeToType("task.progress", this.handleTaskEvent),
        taskBusStore.subscribeToType("task.completed", this.handleTaskEvent),
        taskBusStore.subscribeToType("task.failed", this.handleTaskEvent)
      ];

      this._taskUnsubscriber = () => {
        unsubscribers.forEach((unsubscribe) => unsubscribe());
      };
    },

    handleTaskEvent(event: TaskEvent): void {
      if (
        event.projectId !== this.projectId ||
        (event.taskType !== "ai_voice" && event.taskType !== "tts_generation")
      ) {
        return;
      }

      if (event.type === "task.started" || event.type === "task.progress") {
        this.activeTask = {
          id: event.taskId ?? "",
          task_type: event.taskType ?? "ai_voice",
          project_id: event.projectId ?? this.projectId,
          status: "running",
          progress: event.progressPct ?? event.progress ?? 0,
          message: event.message ?? "正在生成配音草稿…",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        this.status = "generating";
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
        this.applyInputError(event.errorMessage ?? "配音生成失败，请稍后重试。");
      }
    },

    async refreshTracks(): Promise<void> {
      if (!this.projectId) {
        return;
      }

      try {
        const tracks = await fetchVoiceTracks(this.projectId);
        this.tracks = tracks;
        this.trackDetailsById = {
          ...this.trackDetailsById,
          ...Object.fromEntries(tracks.map((track) => [track.id, track]))
        };
        this.selectedTrackId = tracks[0]?.id ?? null;

        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },

    async refreshProfiles(providerId = "volcengine_tts"): Promise<VoiceProfileRefreshResultDto | null> {
      this.profileSyncing = true;
      this.error = null;

      try {
        const result = await refreshVoiceProfiles(providerId);
        this.profiles = this.filterSupportedProfiles(await fetchVoiceProfiles());
        this.selectedProfileId = this.resolveProfileSelection(this.profiles);
        this.status = this.resolveStatus();
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      } finally {
        this.profileSyncing = false;
      }
    },

    async generate(): Promise<VoiceTrackGenerateResultDto | null> {
      if (!this.projectId) {
        this.applyInputError("请先选择有效项目。");
        return null;
      }

      const sourceText = this.sourceText.trim();
      if (!sourceText) {
        this.applyInputError("脚本文本为空，无法生成配音。");
        return null;
      }

      if (!this.selectedProfileId) {
        this.applyInputError("请先选择配音角色，并确认 AI 与系统设置中已启用配音能力。");
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

        if (result.track) {
          this.upsertTrack(result.track);
          this.trackDetailsById = {
            ...this.trackDetailsById,
            [result.track.id]: result.track
          };
          this.selectedTrackId = result.track.id;
        }

        this.status = result.track?.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },

    extractParagraphs(documentJson: Record<string, any> | null, content = ""): Paragraph[] {
      return extractScriptDocumentDownstreamText(documentJson, "voice", content);
    },

    selectProfile(profileId: string): void {
      this.selectedProfileId = profileId;
      this.status = this.resolveStatus();
    },

    async selectTrack(trackId: string): Promise<void> {
      this.selectedTrackId = trackId;
      await this.loadTrackDetail(trackId, true);

      if (!this.error) {
        this.status = this.resolveStatus();
      }
    },

    async deleteTrack(trackId: string): Promise<void> {
      if (!this.projectId) {
        return;
      }

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
      if (
        this.selectedProfileId &&
        profiles.some((profile) => profile.id === this.selectedProfileId)
      ) {
        return this.selectedProfileId;
      }

      return profiles.find((profile) => profile.enabled)?.id ?? null;
    },

    filterSupportedProfiles(profiles: VoiceProfileDto[]): VoiceProfileDto[] {
      return profiles.filter((profile) => profile.provider === "volcengine_tts");
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
      if (this.error) {
        return "error";
      }
      if (!this.paragraphs.length) {
        return "empty";
      }
      if (this.selectedTrackId && this.trackDetailsById[this.selectedTrackId]?.status === "blocked") {
        return "blocked";
      }
      if (!this.profiles.some((profile) => profile.enabled)) {
        return "blocked";
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
      this.error = toRuntimeErrorShape(error, "请求配音相关数据失败，请检查 Runtime 状态后重试。");
    }
  }
});
