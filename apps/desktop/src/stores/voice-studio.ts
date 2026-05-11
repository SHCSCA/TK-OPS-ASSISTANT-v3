import { defineStore } from "pinia";

import {
  deleteVoiceTrack,
  fetchScriptDocument,
  fetchStoryboardDocument,
  fetchVoiceProfiles,
  fetchVoiceTrack,
  fetchVoiceTracks,
  generateVoiceTrack,
  refreshVoiceProfiles
} from "@/app/runtime-client";
import { useToast } from "@/composables/useToast";
import { extractScriptDocumentDownstreamText } from "@/modules/scripts/script-document-view-model";
import { toRuntimeErrorShape } from "@/stores/runtime-store-helpers";
import { useTaskBusStore } from "@/stores/task-bus";
import type {
  RuntimeRequestErrorShape,
  ScriptDocument,
  StoryboardDocument,
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
  /** 显示文本（含时间前缀，用于界面展示） */
  text: string;
  /** 纯语音文本（不含时间前缀，用于 TTS 合成） */
  speechText: string;
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
    sourceText: (state): string => state.paragraphs.map((paragraph) => paragraph.speechText).join("\n"),
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
        // 并行获取脚本、分镜、音色、音轨数据；分镜请求失败不阻断主流程
        const [document, storyboard, profiles, tracks] = await Promise.all([
          fetchScriptDocument(projectId),
          fetchStoryboardDocument(projectId).catch(() => null as StoryboardDocument | null),
          fetchVoiceProfiles(),
          fetchVoiceTracks(projectId)
        ]);

        this.document = document;
        this.profiles = this.filterSupportedProfiles(profiles);
        this.tracks = tracks;
        this.trackDetailsById = Object.fromEntries(tracks.map((track) => [track.id, track]));

        // 优先使用分镜数据作为段落来源，回退到脚本文稿
        const storyboardParagraphs = this.extractStoryboardParagraphs(storyboard);
        this.paragraphs = storyboardParagraphs.length > 0
          ? storyboardParagraphs
          : this.extractParagraphs(
              document.currentVersion?.documentJson ?? null,
              document.currentVersion?.content ?? ""
            );

        this.activeParagraphIndex = 0;
        this.selectedProfileId = this.resolveProfileSelection(this.profiles);
        this.selectedTrackId = tracks[0]?.id ?? null;

        if (this.selectedTrackId) {
          await this.loadTrackDetail(this.selectedTrackId, false);
        }

        this.status = this.activeTask && isActiveTaskStatus(this.activeTask.status)
          ? "generating"
          : "ready";
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
      const matchesActiveTask = Boolean(event.taskId && event.taskId === this.activeTask?.id);
      const matchesVoiceTaskType = isVoiceTaskType(event.taskType);
      if (
        (event.projectId && event.projectId !== this.projectId) ||
        (!matchesVoiceTaskType && !matchesActiveTask)
      ) {
        return;
      }

      if (event.type === "task.started" || event.type === "task.progress") {
        this.activeTask = {
          id: event.taskId ?? "",
          task_type: event.taskType ?? this.activeTask?.task_type ?? "ai-voice",
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
        const toast = useToast();
        toast.success("配音生成完成", "音轨已就绪，可在左侧预览试听。");
        return;
      }

      if (event.type === "task.failed") {
        this.activeTask = null;
        this.applyInputError(event.errorMessage ?? "配音生成失败，请稍后重试。");
        const toast = useToast();
        toast.danger("配音生成失败", event.errorMessage ?? "请稍后重试。");
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
      const toast = useToast();
      toast.info("配音任务已提交", "正在生成整段音轨，请稍候…");

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

        if (result.track?.status === "blocked") {
          this.activeTask = null;
          this.status = "blocked";
          toast.warning("配音已保存为草稿", result.message || "缺少 TTS Provider，无法生成真实音频。");
        } else if (result.task) {
          this.activeTask = normalizeTaskInfo(result.task, this.projectId);
          this.status = this.activeTask && isActiveTaskStatus(this.activeTask.status)
            ? "generating"
            : "ready";
        } else if (isTrackGenerating(result.track?.status)) {
          this.status = "generating";
        } else {
          this.activeTask = null;
          this.status = "ready";
        }
        return result;
      } catch (err) {
        this.applyRuntimeError(err);
        const errMsg = (this as VoiceStudioState).error?.message ?? "请稍后重试。";
        toast.danger("配音生成失败", errMsg);
        return null;
      }
    },

    extractParagraphs(documentJson: Record<string, any> | null, content = ""): Paragraph[] {
      const lines = extractScriptDocumentDownstreamText(documentJson, "voice", content);
      return lines.map((line) => ({ ...line, speechText: line.text }));
    },

    /**
     * 从分镜数据提取配音段落，优先使用 voiceover 字段，回退到 subtitle。
     * 每段以时间标记为前缀（如 "0-2s: Watch closely..."）。
     */
    extractStoryboardParagraphs(storyboard: StoryboardDocument | null): Paragraph[] {
      if (!storyboard?.currentVersion?.scenes?.length) {
        return [];
      }

      const scenes = storyboard.currentVersion.scenes;
      const paragraphs: Paragraph[] = [];

      for (const scene of scenes) {
        const speechText = (scene.voiceover || scene.subtitle || "").trim();
        if (!speechText) {
          continue;
        }

        // 拼接时间前缀（如果有），仅用于界面展示
        const timePrefix = scene.time ? `${scene.time}: ` : "";
        const displayText = `${timePrefix}${speechText}`;

        // 估算时长：按中文 4 字/秒、英文 3 词/秒混合估算
        const estimatedDuration = this.estimateSegmentDuration(speechText);

        paragraphs.push({ text: displayText, speechText, estimatedDuration });
      }

      return paragraphs;
    },

    /** 估算文本朗读时长（秒），中文按 4 字/秒，英文按 3 词/秒 */
    estimateSegmentDuration(text: string): number {
      // 中文字符数
      const chineseChars = (text.match(/[一-鿿]/g) || []).length;
      // 英文单词数（去除中文后按空格分词）
      const nonChinese = text.replace(/[一-鿿]/g, " ").trim();
      const englishWords = nonChinese ? nonChinese.split(/\s+/).filter(Boolean).length : 0;

      const duration = chineseChars / 4 + englishWords / 3;
      return Math.max(1, Math.round(duration));
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
        this.syncActiveTaskFromTrack(detail);
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
      if (this.activeTask && isActiveTaskStatus(this.activeTask.status)) {
        return "generating";
      }
      if (isTrackGenerating(this.selectedTrack?.status)) {
        return "generating";
      }
      if (this.selectedTrackId && this.trackDetailsById[this.selectedTrackId]?.status === "blocked") {
        return "blocked";
      }
      return "ready";
    },

    syncActiveTaskFromTrack(track: VoiceTrackDto): void {
      const activeTask = normalizeTaskInfo(track.activeTask, this.projectId);
      if (activeTask && isActiveTaskStatus(activeTask.status)) {
        this.activeTask = activeTask;
      }
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

const VOICE_TASK_TYPES = new Set(["ai-voice", "ai_voice", "tts_generation"]);

type RuntimeVoiceTask = Partial<TaskInfo> & {
  kind?: unknown;
  taskType?: unknown;
  projectId?: unknown;
  progressPct?: unknown;
  createdAt?: unknown;
  updatedAt?: unknown;
  status?: unknown;
};

function isVoiceTaskType(taskType: string | null | undefined): boolean {
  return typeof taskType === "string" && VOICE_TASK_TYPES.has(taskType);
}

function isActiveTaskStatus(status: TaskInfo["status"]): boolean {
  return status === "queued" || status === "running";
}

function isTrackGenerating(status: VoiceTrackDto["status"] | null | undefined): boolean {
  return status === "generating" || status === "processing" || status === "queued" || status === "running";
}

function normalizeTaskInfo(rawTask: unknown, fallbackProjectId: string): TaskInfo | null {
  if (!rawTask || typeof rawTask !== "object") {
    return null;
  }

  const task = rawTask as RuntimeVoiceTask;
  const id = asString(task.id);
  if (!id) {
    return null;
  }

  const now = new Date().toISOString();
  const taskType =
    asString(task.task_type) ??
    asString(task.taskType) ??
    asString(task.kind) ??
    "ai-voice";

  return {
    id,
    task_type: taskType,
    project_id: asString(task.project_id) ?? asString(task.projectId) ?? fallbackProjectId,
    status: normalizeTaskStatus(task.status),
    progress: normalizeProgress(task.progressPct ?? task.progress),
    message: asString(task.message) ?? "正在生成配音草稿…",
    created_at: asString(task.created_at) ?? asString(task.createdAt) ?? now,
    updated_at: asString(task.updated_at) ?? asString(task.updatedAt) ?? now
  };
}

function normalizeTaskStatus(status: unknown): TaskInfo["status"] {
  if (
    status === "queued" ||
    status === "running" ||
    status === "succeeded" ||
    status === "failed" ||
    status === "cancelled"
  ) {
    return status;
  }
  return "queued";
}

function normalizeProgress(value: unknown): number {
  const progress = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(progress)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(progress)));
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}
