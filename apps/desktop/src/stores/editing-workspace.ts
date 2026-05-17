import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  assembleWorkspaceTimeline,
  createWorkspaceTimeline,
  deleteWorkspaceClip,
  fetchAssets,
  fetchWorkspaceTimeline,
  moveWorkspaceClip,
  precheckTimeline,
  runWorkspaceAICommand,
  splitWorkspaceClip,
  trimWorkspaceClip,
  updateWorkspaceTimeline
} from "@/app/runtime-client";
import type {
  AssetDto,
  RuntimeRequestErrorShape,
  TimelinePrecheckDto,
  WorkspaceAICommandResultDto,
  WorkspaceAssemblyStateDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineResultDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

export type EditingWorkspaceStatus =
  | "idle"
  | "loading"
  | "empty"
  | "ready"
  | "saving"
  | "blocked"
  | "error";

export type EditingWorkspaceAssetStatus = "idle" | "loading" | "ready" | "error";

type EditingWorkspaceState = {
  assemblyState: WorkspaceAssemblyStateDto | null;
  assetError: RuntimeRequestErrorShape | null;
  assetStatus: EditingWorkspaceAssetStatus;
  assets: AssetDto[];
  blockedMessage: string | null;
  error: RuntimeRequestErrorShape | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  precheck: TimelinePrecheckDto | null;
  projectId: string;
  playheadMs: number;
  saveState: WorkspaceSaveStateDto | null;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
};

export const useEditingWorkspaceStore = defineStore("editing-workspace", {
  state: (): EditingWorkspaceState => ({
    assemblyState: null,
    assetError: null,
    assetStatus: "idle",
    assets: [],
    blockedMessage: null,
    error: null,
    lastCommandResult: null,
    precheck: null,
    projectId: "",
    playheadMs: 0,
    saveState: null,
    selectedClipId: null,
    selectedTrackId: null,
    status: "idle",
    timeline: null
  }),
  getters: {
    hasTimeline: (state): boolean => state.timeline !== null,
    orderedTracks: (state): WorkspaceTimelineTrackDto[] =>
      [...(state.timeline?.tracks ?? [])].sort((a, b) => a.orderIndex - b.orderIndex),
    viewState: (state): "loading" | "empty" | "ready" | "error" | "blocked" =>
      state.status === "idle" || state.status === "loading" || state.status === "saving"
        ? "loading"
        : state.status,
    selectedTrack: (state): WorkspaceTimelineTrackDto | null =>
      state.timeline?.tracks.find((track) => track.id === state.selectedTrackId) ?? null,
    selectedClip: (state) => {
      const clips = state.timeline?.tracks.flatMap((track) => track.clips) ?? [];
      return clips.find((clip) => clip.id === state.selectedClipId) ?? null;
    },
    isBusy: (state): boolean => state.status === "loading" || state.status === "saving"
  },
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      this.lastCommandResult = null;
      this.precheck = null;
      this.assets = [];
      this.assetStatus = "idle";
      this.assetError = null;

      try {
        this.applyTimelineResult(await fetchWorkspaceTimeline(projectId));
        await this.loadAssets(projectId);
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async loadAssets(projectId?: string): Promise<AssetDto[]> {
      if (!projectId) {
        this.assets = [];
        this.assetStatus = "idle";
        this.assetError = null;
        return [];
      }

      this.assetStatus = "loading";
      this.assetError = null;

      try {
        const assets = (await fetchAssets()).filter(
          (asset) => asset.projectId === projectId || asset.sourceInfo.projectId === projectId
        );
        this.assets = assets;
        this.assetStatus = "ready";
        this.assetError = null;
        return assets;
      } catch (error) {
        const runtimeError =
          error instanceof RuntimeRequestError
            ? error
            : new RuntimeRequestError("资产读取失败，请稍后重试。");
        this.assets = [];
        this.assetStatus = "error";
        this.assetError = {
          details: runtimeError.details,
          message: runtimeError.message,
          requestId: runtimeError.requestId,
          status: runtimeError.status
        };
        return [];
      }
    },
    async createDraft(projectId?: string, name = "主时间线"): Promise<WorkspaceTimelineDto | null> {
      const pid = projectId || this.projectId;
      if (!pid) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.projectId = pid;

      try {
        const result = await createWorkspaceTimeline(pid, { name });
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async assembleTimeline(projectId?: string): Promise<WorkspaceTimelineDto | null> {
      const pid = projectId || this.projectId;
      if (!pid) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.projectId = pid;
      this.precheck = null;

      try {
        const result = await assembleWorkspaceTimeline(pid, {
          mode: "merge_managed",
          timelineName: this.timeline?.name ?? "主时间线"
        });
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async runPrecheck(): Promise<TimelinePrecheckDto | null> {
      if (!this.timeline) {
        this.applyInputError("当前项目还没有时间线草稿。");
        return null;
      }

      this.status = "saving";
      this.error = null;

      try {
        const result = await precheckTimeline(this.timeline.id);
        this.precheck = result;
        this.blockedMessage = result.status === "warning" ? result.message ?? "时间线预检发现问题。" : null;
        this.status = "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async saveTimeline(): Promise<WorkspaceTimelineDto | null> {
      if (!this.timeline) {
        this.applyInputError("当前项目还没有时间线草稿。");
        return null;
      }

      this.status = "saving";
      this.error = null;

      try {
        const result = await updateWorkspaceTimeline(this.timeline.id, {
          name: this.timeline.name,
          durationSeconds: this.timeline.durationSeconds,
          tracks: this.timeline.tracks
        });
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async runMagicCut(projectId?: string): Promise<WorkspaceAICommandResultDto | null> {
      const pid = projectId || this.projectId;
      if (!pid) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.projectId = pid;

      try {
        const result = await runWorkspaceAICommand(pid, {
          timelineId: this.timeline?.id ?? null,
          capabilityId: "magic_cut",
          parameters: {
            selectedTrackId: this.selectedTrackId,
            selectedClipId: this.selectedClipId
          }
        });
        this.lastCommandResult = result;
        this.blockedMessage = result.status === "blocked" ? result.message : null;
        this.status = result.status === "blocked" ? "blocked" : "ready";
        return result;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    selectTrack(trackId: string | null): void {
      this.selectedTrackId = trackId;
      this.selectedClipId = null;
    },
    selectClip(clipId: string | null): void {
      this.selectedClipId = clipId;
    },
    setPlayheadMs(value: number): void {
      const durationMs = this.resolveTimelineDurationMs();
      const roundedValue = Number.isFinite(value) ? Math.round(value) : 0;
      this.playheadMs = Math.min(durationMs, Math.max(0, roundedValue));
    },
    async deleteSelectedClip(): Promise<WorkspaceTimelineDto | null> {
      if (!this.selectedClipId) {
        this.applyInputError("请先选择要删除的片段。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await deleteWorkspaceClip(this.selectedClipId);
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async splitSelectedClip(): Promise<WorkspaceTimelineDto | null> {
      const clip = this.findClipById(this.selectedClipId);
      if (!clip) {
        this.applyInputError("请先选择要分割的片段。");
        return null;
      }
      if (clip.durationMs < 2) {
        this.applyInputError("片段时长过短，无法分割。");
        return null;
      }
      const clipEndMs = clip.startMs + clip.durationMs;
      if (this.playheadMs <= clip.startMs || this.playheadMs >= clipEndMs) {
        this.applyInputError("播放头必须位于选中片段内部才能分割。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await splitWorkspaceClip(clip.id, {
          splitAtMs: this.playheadMs
        });
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async moveSelectedClipBy(deltaMs: number): Promise<WorkspaceTimelineDto | null> {
      const clip = this.findClipById(this.selectedClipId);
      if (!clip) {
        this.applyInputError("请先选择要移动的片段。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await moveWorkspaceClip(clip.id, {
          targetTrackId: clip.trackId,
          startMs: Math.max(0, clip.startMs + deltaMs)
        });
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async trimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<WorkspaceTimelineDto | null> {
      const clip = this.findClipById(this.selectedClipId);
      if (!clip) {
        this.applyInputError("请先选择要裁剪的片段。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await trimWorkspaceClip(
          clip.id,
          edge === "left"
            ? {
                startMs: Math.max(0, clip.startMs + deltaMs),
                durationMs: clip.durationMs - deltaMs,
                inPointMs: Math.max(0, clip.inPointMs + deltaMs)
              }
            : { durationMs: clip.durationMs + deltaMs }
        );
        this.applyTimelineResult(result);
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    applyTimelineResult(result: WorkspaceTimelineResultDto): void {
      this.timeline = result.timeline;
      this.blockedMessage = result.timeline ? null : result.message;
      this.saveState = result.saveState ?? null;
      this.assemblyState = result.assemblyState ?? null;
      this.selectedTrackId = this.resolveSelectedTrackId();
      this.selectedClipId = this.resolveSelectedClipId();
      this.setPlayheadMs(this.playheadMs);
      this.status = result.timeline ? "ready" : "empty";
    },
    resolveSelectedTrackId(): string | null {
      if (!this.timeline) return null;
      if (this.selectedTrackId && this.timeline.tracks.some((track) => track.id === this.selectedTrackId)) {
        return this.selectedTrackId;
      }
      return this.timeline.tracks[0]?.id ?? null;
    },
    resolveSelectedClipId(): string | null {
      if (!this.timeline) return null;
      const clips = this.timeline.tracks.flatMap((track) => track.clips);
      if (this.selectedClipId && clips.some((clip) => clip.id === this.selectedClipId)) {
        return this.selectedClipId;
      }
      return null;
    },
    findClipById(clipId: string | null): WorkspaceTimelineClipDto | null {
      if (!clipId || !this.timeline) return null;
      const clips = this.timeline.tracks.flatMap((track) => track.clips);
      return clips.find((clip) => clip.id === clipId) ?? null;
    },
    resolveTimelineDurationMs(): number {
      const declaredDurationMs = Math.max(0, Math.round((this.timeline?.durationSeconds ?? 0) * 1000));
      const clips = this.timeline?.tracks.flatMap((track) => track.clips) ?? [];
      const clipEndMs = clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0);
      return Math.max(declaredDurationMs, clipEndMs, 0);
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
          : new RuntimeRequestError("AI 剪辑工作台请求失败");
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
