import { defineStore } from "pinia";

import {
  deleteVoiceTrack,
  fetchScriptDocument,
  fetchVoiceTrack,
  fetchVoiceProfiles,
  fetchVoiceTracks,
  generateVoiceTrack
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  VoiceProfileDto,
  VoiceTrackDto,
  VoiceTrackGenerateResultDto
} from "@/types/runtime";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";
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
  activeTask: TaskInfo | null;
  _taskUnsubscriber: (() => void) | null;
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
    tracks: [],
    activeTask: null,
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
      this._taskUnsubscriber = taskBusStore.subscribeToType("ai-voice", (event: TaskEvent) => {
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
          message: event.message ?? "正在配音...",
          task_type: "ai-voice",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        } as any;
        this.status = "generating";
      } else if (event.type === "task.completed") {
        this.activeTask = null;
        this.status = "ready";
        void this.refreshTracks();
      } else if (event.type === "task.failed") {
        this.activeTask = null;
        this.status = "error";
        this.applyInputError(event.errorMessage ?? "配音生成失败");
      }
    },

    async refreshTracks(): Promise<void> {
      if (!this.projectId) return;
      try {
        const tracks = await fetchVoiceTracks(this.projectId);
        this.tracks = tracks;
        // Optionally select the latest track if just finished
        if (tracks.length > 0) {
          this.selectedTrackId = tracks[0].id;
          await this.loadTrackDetail(tracks[0].id, false);
        }
      } catch (e) {
        console.error("Failed to refresh tracks:", e);
      }
    },

    async generate(): Promise<VoiceTrackGenerateResultDto | null> {
      if (!this.projectId) {
        this.applyInputError("未选择有效项目。");
        return null;
      }

      const sourceText = this.sourceText.trim();
      if (!sourceText) {
        this.applyInputError("当前项目尚无文案内容，请先在脚本中心完成创作并保存。");
        return null;
      }

      if (!this.selectedProfileId) {
        this.applyInputError("请先选择配音角色，并在 AI 系统设置中确保已开启配音能力。");
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
        
        // If task was submitted, wait for events. If immediate, status becomes ready.
        this.status = result.track?.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    
    extractParagraphs(content: string): Paragraph[] {
      return content
        .split(/\n\s*\n/) // split by empty lines
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
      this.error = toRuntimeErrorShape(error, "请求配音相关数据失败，请检查网络或后端状态。");
    }
  }
});
