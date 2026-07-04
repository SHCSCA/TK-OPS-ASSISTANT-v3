import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  applyMagicCutSuggestion as applyRuntimeMagicCutSuggestion,
  assembleWorkspaceTimeline,
  createWorkspaceTimeline,
  deleteWorkspaceClip,
  dismissMagicCutSuggestion as dismissRuntimeMagicCutSuggestion,
  fetchAssets,
  fetchLatestMagicCutSuggestion,
  fetchTimelinePreview,
  fetchWorkspaceTimeline,
  insertWorkspaceAssetClip,
  moveWorkspaceClip,
  precheckTimeline,
  replaceWorkspaceClip,
  runWorkspaceAICommand,
  splitWorkspaceClip,
  trimWorkspaceClip,
  cancelTask,
  updateWorkspaceTimeline
} from "@/app/runtime-client";
import {
  buildWorkspacePreviewContext,
  type WorkspacePreviewContext
} from "@/modules/workspace/workspacePreviewContext";
import {
  createTimelineHistorySaveState,
  createWorkspaceTimelineHistorySnapshot,
  createWorkspaceTimelineUpdateInput,
  type WorkspaceTimelineHistorySnapshot
} from "@/modules/workspace/workspaceTimelineHistory";
import type {
  AssetDto,
  MagicCutSuggestionApplyResultDto,
  MagicCutSuggestionDraftDto,
  RuntimeRequestErrorShape,
  TimelinePrecheckDto,
  TimelinePrecheckIssueDetailDto,
  TimelinePreviewDto,
  WorkspaceAICommandResultDto,
  WorkspaceAssemblyStateDto,
  WorkspaceSaveStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineResultDto
} from "@/types/runtime";
import type { TaskInfo, TaskStatus } from "@/types/task-events";

export type EditingWorkspaceStatus =
  | "idle"
  | "loading"
  | "empty"
  | "ready"
  | "saving"
  | "blocked"
  | "error";

export type EditingWorkspaceAssetStatus = "idle" | "loading" | "ready" | "error";

export type MagicCutSuggestionStatus = "idle" | "loading" | "ready" | "applying" | "error";

export type EditingWorkspaceMovePreview = {
  gesture: "move";
  clipId: string;
  trackId: string;
  startMs: number;
  durationMs: number;
};

export type EditingWorkspaceTrimPreview = {
  gesture: "trim";
  clipId: string;
  trackId: string;
  edge: "left" | "right";
  startMs: number;
  durationMs: number;
  inPointMs?: number;
};

type EditingWorkspaceState = {
  assemblyState: WorkspaceAssemblyStateDto | null;
  assetError: RuntimeRequestErrorShape | null;
  assetStatus: EditingWorkspaceAssetStatus;
  assets: AssetDto[];
  blockedMessage: string | null;
  error: RuntimeRequestErrorShape | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  magicCutSuggestion: MagicCutSuggestionDraftDto | null;
  magicCutSuggestionError: RuntimeRequestErrorShape | null;
  magicCutSuggestionStatus: MagicCutSuggestionStatus;
  precheck: TimelinePrecheckDto | null;
  preview: TimelinePreviewDto | null;
  previewError: RuntimeRequestErrorShape | null;
  previewRequestId: number;
  projectId: string;
  playheadMs: number;
  saveState: WorkspaceSaveStateDto | null;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
  timelineRedoSnapshot: WorkspaceTimelineHistorySnapshot | null;
  timelineUndoSnapshot: WorkspaceTimelineHistorySnapshot | null;
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
    magicCutSuggestion: null,
    magicCutSuggestionError: null,
    magicCutSuggestionStatus: "idle",
    precheck: null,
    preview: null,
    previewError: null,
    previewRequestId: 0,
    projectId: "",
    playheadMs: 0,
    saveState: null,
    selectedClipId: null,
    selectedTrackId: null,
    status: "idle",
    timeline: null,
    timelineRedoSnapshot: null,
    timelineUndoSnapshot: null
  }),
  getters: {
    canRedoTimelineEdit: (state): boolean => state.timelineRedoSnapshot !== null,
    canUndoTimelineEdit: (state): boolean => state.timelineUndoSnapshot !== null,
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
    previewContext: (state): WorkspacePreviewContext => {
      const selectedTrack =
        state.timeline?.tracks.find((track) => track.id === state.selectedTrackId) ?? null;
      const clips = state.timeline?.tracks.flatMap((track) => track.clips) ?? [];
      const selectedClip = clips.find((clip) => clip.id === state.selectedClipId) ?? null;

      return buildWorkspacePreviewContext({
        playheadMs: state.playheadMs,
        timelinePreview: state.preview,
        timelinePreviewErrorMessage: state.previewError?.message ?? null,
        selectedClip,
        selectedTrack,
        timeline: state.timeline
      });
    },
    isBusy: (state): boolean => state.status === "loading" || state.status === "saving"
  },
  actions: {
    async load(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;
      this.projectId = projectId;
      this.lastCommandResult = null;
      this.magicCutSuggestion = null;
      this.magicCutSuggestionStatus = "idle";
      this.magicCutSuggestionError = null;
      this.precheck = null;
      this.preview = null;
      this.previewError = null;
      this.assets = [];
      this.assetStatus = "idle";
      this.assetError = null;

      try {
        this.applyTimelineResult(await fetchWorkspaceTimeline(projectId));
        this.clearTimelineHistory();
        await this.refreshTimelinePreview();
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
        this.clearTimelineHistory();
        await this.refreshTimelinePreview();
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
      this.lastCommandResult = null;
      this.magicCutSuggestion = null;
      this.magicCutSuggestionStatus = "idle";
      this.magicCutSuggestionError = null;

      try {
        const result = await assembleWorkspaceTimeline(pid, {
          mode: "merge_managed",
          timelineName: this.timeline?.name ?? "主时间线"
        });
        this.applyTimelineResult(result);
        this.clearTimelineHistory();
        await this.refreshTimelinePreview();
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
      this.lastCommandResult = null;

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
      this.lastCommandResult = null;

      try {
        const result = await updateWorkspaceTimeline(
          this.timeline.id,
          createWorkspaceTimelineUpdateInput(this.timeline)
        );
        this.applyTimelineResult(result);
        await this.refreshTimelinePreview();
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
      this.precheck = null;
      this.lastCommandResult = null;
      this.magicCutSuggestion = null;
      this.magicCutSuggestionStatus = "idle";
      this.magicCutSuggestionError = null;

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
        if (isMagicCutPrecheckError(error)) {
          this.applyBlockedMessage(buildMagicCutUnavailableMessage(error.message));
          return this.lastCommandResult;
        }
        this.applyRuntimeError(error);
        return null;
      }
    },
    async cancelCommandTask(taskId: string): Promise<WorkspaceAICommandResultDto | null> {
      if (!taskId) {
        this.applyInputError("当前没有可取消的 AI 任务。");
        return null;
      }

      this.status = "saving";
      this.error = null;

      try {
        const result = await cancelTask(taskId);
        const status = normalizeCommandTaskStatus(result.status);
        const now = new Date().toISOString();
        const task: TaskInfo = {
          id: result.task_id || taskId,
          task_type: "ai-workspace-command",
          project_id: this.projectId || null,
          status,
          progress: status === "succeeded" ? 100 : 0,
          message: result.message || "AI 任务状态已更新。",
          created_at: now,
          updated_at: now
        };
        const commandResult: WorkspaceAICommandResultDto = {
          status,
          task,
          message: task.message
        };

        this.lastCommandResult = commandResult;
        this.blockedMessage = null;
        this.status = "ready";
        return commandResult;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async applyCommandTerminalTask(task: TaskInfo): Promise<void> {
      const commandResult: WorkspaceAICommandResultDto = {
        status: task.status,
        task,
        message: task.message || "AI 命令状态已更新。"
      };

      this.lastCommandResult = commandResult;
      if (task.status !== "succeeded" || !this.projectId) return;

      const suggestion = await this.loadMagicCutSuggestion();
      this.lastCommandResult = {
        ...commandResult,
        message: suggestion
          ? commandResult.message
          : appendCommandTerminalSuggestionLoadFailedMessage(commandResult.message)
      };
    },
    async loadMagicCutSuggestion(): Promise<MagicCutSuggestionDraftDto | null> {
      if (!this.projectId || !this.timeline) {
        this.magicCutSuggestion = null;
        this.magicCutSuggestionStatus = "idle";
        this.magicCutSuggestionError = null;
        return null;
      }

      this.magicCutSuggestionStatus = "loading";
      this.magicCutSuggestionError = null;

      try {
        const suggestion = await fetchLatestMagicCutSuggestion(this.projectId, this.timeline.id);
        this.magicCutSuggestion = suggestion;
        this.magicCutSuggestionStatus = "ready";
        return suggestion;
      } catch (error) {
        this.magicCutSuggestionStatus = "error";
        this.magicCutSuggestionError = toRuntimeErrorShape(
          error,
          "智能粗剪建议读取失败，请稍后重试。"
        );
        return null;
      }
    },
    async applyMagicCutSuggestion(operationIds: string[]): Promise<MagicCutSuggestionApplyResultDto | null> {
      if (!this.magicCutSuggestion) {
        this.applyMagicCutSuggestionError("当前没有可应用的智能粗剪建议。");
        return null;
      }

      this.magicCutSuggestionStatus = "applying";
      this.magicCutSuggestionError = null;

      try {
        const result = await applyRuntimeMagicCutSuggestion(this.magicCutSuggestion.id, {
          operationIds,
          confirmTimelineVersionToken: this.magicCutSuggestion.timelineVersionToken
        });
        this.magicCutSuggestion = result.suggestion;
        this.magicCutSuggestionStatus = "ready";
        this.applyTimelineResult({
          timeline: result.timeline,
          message: result.message
        });
        await this.refreshTimelinePreview();
        const precheckResult = await this.runPrecheck();
        this.lastCommandResult = {
          status: "succeeded",
          task: null,
          message: precheckResult === null
            ? `${result.message} 预检未完成，请手动重试。`
            : `已应用 ${result.appliedCount} 条智能粗剪建议，时间线本地预检通过。`
        };
        return result;
      } catch (error) {
        this.magicCutSuggestionStatus = "error";
        this.magicCutSuggestionError = toRuntimeErrorShape(
          error,
          "应用失败，已保留原时间线。"
        );
        return null;
      }
    },
    async dismissMagicCutSuggestion(): Promise<void> {
      if (!this.magicCutSuggestion) {
        this.magicCutSuggestion = null;
        this.magicCutSuggestionStatus = "ready";
        this.magicCutSuggestionError = null;
        return;
      }

      this.magicCutSuggestionStatus = "applying";
      this.magicCutSuggestionError = null;

      try {
        const result = await dismissRuntimeMagicCutSuggestion(this.magicCutSuggestion.id);
        this.magicCutSuggestion = null;
        this.magicCutSuggestionStatus = "ready";
        this.lastCommandResult = {
          status: "succeeded",
          task: null,
          message: result.message
        };
      } catch (error) {
        this.magicCutSuggestionStatus = "error";
        this.magicCutSuggestionError = toRuntimeErrorShape(
          error,
          "智能粗剪建议忽略失败，请稍后重试。"
        );
      }
    },
    selectTrack(trackId: string | null): void {
      this.selectedTrackId = trackId;
      this.selectedClipId = null;
    },
    selectClip(clipId: string | null): void {
      this.selectedClipId = clipId;
    },
    selectTimelineClip(payload: { clipId: string; trackId: string }): void {
      this.selectedTrackId = payload.trackId;
      this.selectedClipId = payload.clipId;
    },
    focusPrecheckIssue(issue: TimelinePrecheckIssueDetailDto | string): boolean {
      if (!this.timeline) {
        this.blockedMessage = "当前没有可定位的时间线。";
        return false;
      }

      if (typeof issue !== "string") {
        const focusedByDetail = this.focusStructuredPrecheckIssue(issue);
        if (focusedByDetail !== null) return focusedByDetail;
      }

      const normalizedIssue =
        typeof issue === "string" ? issue.trim() : this.buildPrecheckIssueSearchText(issue);
      if (!normalizedIssue) {
        this.blockedMessage = "预检问题内容为空，无法定位。";
        return false;
      }

      const tracks = this.timeline.tracks;
      const clips = tracks.flatMap((track) => track.clips);
      const matchedClip = clips.find(
        (clip) => normalizedIssue.includes(clip.id) || normalizedIssue.includes(clip.label)
      );

      if (matchedClip) {
        this.selectedTrackId = matchedClip.trackId;
        this.selectedClipId = matchedClip.id;
        this.setPlayheadMs(matchedClip.startMs);
        this.blockedMessage = null;
        return true;
      }

      const matchedTrack = tracks.find(
        (track) => normalizedIssue.includes(track.id) || normalizedIssue.includes(track.name)
      );

      if (matchedTrack) {
        this.selectedTrackId = matchedTrack.id;
        this.selectedClipId = null;
        this.setPlayheadMs(matchedTrack.clips[0]?.startMs ?? this.playheadMs);
        this.blockedMessage = null;
        return true;
      }

      if (this.selectedClipId || this.selectedTrackId) {
        this.blockedMessage = "这条预检问题没有明确片段或轨道，已保留当前选中位置。";
        return false;
      }

      this.blockedMessage = "这条预检问题没有可定位的片段或轨道，请先在时间线中手动选择。";
      return false;
    },
    focusStructuredPrecheckIssue(issue: TimelinePrecheckIssueDetailDto): boolean | null {
      if (!this.timeline) return false;

      const targetType = issue.targetType?.trim();
      const targetId = issue.targetId?.trim();
      const clipId = issue.clipId?.trim() || (targetType === "clip" ? targetId : "");
      if (clipId) {
        const clip = this.findClipById(clipId);
        if (clip) {
          this.selectedTrackId = clip.trackId;
          this.selectedClipId = clip.id;
          this.setPlayheadMs(clip.startMs);
          this.blockedMessage = null;
          return true;
        }
      }

      const trackId = issue.trackId?.trim() || (targetType === "track" ? targetId : "");
      if (trackId) {
        const track = this.timeline.tracks.find((item) => item.id === trackId);
        if (track) {
          this.selectedTrackId = track.id;
          this.selectedClipId = null;
          this.setPlayheadMs(track.clips[0]?.startMs ?? this.playheadMs);
          this.blockedMessage = `已定位到轨道：${track.name}。`;
          return true;
        }
      }

      if (clipId || trackId) {
        this.blockedMessage = "预检问题指向的片段或轨道不存在，请刷新时间线后重试。";
        return false;
      }

      return null;
    },
    buildPrecheckIssueSearchText(issue: TimelinePrecheckIssueDetailDto): string {
      return [
        issue.message,
        issue.suggestion,
        issue.targetType,
        issue.targetId,
        issue.targetLabel,
        issue.clipId,
        issue.trackId
      ]
        .map((item) => item?.trim() ?? "")
        .filter(Boolean)
        .join(" ");
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

      const undoSnapshot = this.createTimelineHistorySnapshot();
      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await deleteWorkspaceClip(this.selectedClipId);
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
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

      const undoSnapshot = this.createTimelineHistorySnapshot();
      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await splitWorkspaceClip(clip.id, {
          splitAtMs: this.playheadMs
        });
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
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

      const undoSnapshot = this.createTimelineHistorySnapshot();
      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await moveWorkspaceClip(clip.id, {
          targetTrackId: clip.trackId,
          startMs: Math.max(0, clip.startMs + deltaMs)
        });
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async commitMovePreview(payload: EditingWorkspaceMovePreview): Promise<WorkspaceTimelineDto | null> {
      const originalTimeline = this.timeline;
      const originalSelectedTrackId = this.selectedTrackId;
      const originalSelectedClipId = this.selectedClipId;
      const undoSnapshot = this.createTimelineHistorySnapshot();

      if (!this.findClipById(payload.clipId)) {
        this.applyInputError("请先选择要移动的片段。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;
      this.selectedTrackId = payload.trackId;
      this.selectedClipId = payload.clipId;

      try {
        const result = await moveWorkspaceClip(payload.clipId, {
          targetTrackId: payload.trackId,
          startMs: Math.max(0, Math.round(payload.startMs))
        });
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
        return result.timeline;
      } catch (error) {
        this.timeline = originalTimeline;
        this.selectedTrackId = originalSelectedTrackId;
        this.selectedClipId = originalSelectedClipId;
        this.applyRuntimeError(error, "已恢复到操作前时间线。");
        return null;
      }
    },
    async commitTrimPreview(payload: EditingWorkspaceTrimPreview): Promise<WorkspaceTimelineDto | null> {
      const originalTimeline = this.timeline;
      const originalSelectedTrackId = this.selectedTrackId;
      const originalSelectedClipId = this.selectedClipId;
      const undoSnapshot = this.createTimelineHistorySnapshot();
      const clip = this.findClipById(payload.clipId);

      if (!clip) {
        this.applyInputError("请先选择要裁剪的片段。");
        return null;
      }

      const startMs = Math.max(0, Math.round(payload.startMs));
      const durationMs = Math.max(0, Math.round(payload.durationMs));
      const leftDeltaMs = startMs - clip.startMs;
      const trimInput =
        payload.edge === "left"
          ? {
              startMs,
              durationMs,
              inPointMs: Math.max(0, Math.round(payload.inPointMs ?? clip.inPointMs + leftDeltaMs))
            }
          : { durationMs };

      this.status = "saving";
      this.error = null;
      this.precheck = null;
      this.selectedTrackId = payload.trackId;
      this.selectedClipId = payload.clipId;

      try {
        const result = await trimWorkspaceClip(payload.clipId, trimInput);
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
        return result.timeline;
      } catch (error) {
        this.timeline = originalTimeline;
        this.selectedTrackId = originalSelectedTrackId;
        this.selectedClipId = originalSelectedClipId;
        this.applyRuntimeError(error, "已恢复到操作前时间线。");
        return null;
      }
    },
    async trimSelectedClip(edge: "left" | "right", deltaMs: number): Promise<WorkspaceTimelineDto | null> {
      const clip = this.findClipById(this.selectedClipId);
      if (!clip) {
        this.applyInputError("请先选择要裁剪的片段。");
        return null;
      }

      const undoSnapshot = this.createTimelineHistorySnapshot();
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
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async insertAssetAtPlayhead(assetId: string): Promise<WorkspaceTimelineDto | null> {
      const originalTimeline = this.timeline;
      const originalSelectedTrackId = this.selectedTrackId;
      const originalSelectedClipId = this.selectedClipId;
      const undoSnapshot = this.createTimelineHistorySnapshot();

      if (!this.timeline) {
        this.applyInputError("当前项目还没有时间线草稿。");
        return null;
      }

      const startMs = this.playheadMs;
      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await insertWorkspaceAssetClip(this.timeline.id, {
          assetId,
          startMs
        });
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        this.selectInsertedAssetClip(assetId, startMs);
        await this.refreshTimelinePreview();
        return result.timeline;
      } catch (error) {
        this.timeline = originalTimeline;
        this.selectedTrackId = originalSelectedTrackId;
        this.selectedClipId = originalSelectedClipId;
        this.applyRuntimeError(error, "已恢复到操作前时间线。");
        return null;
      }
    },
    async replaceSelectedClipWithAsset(assetId: string): Promise<WorkspaceTimelineDto | null> {
      const originalTimeline = this.timeline;
      const originalSelectedTrackId = this.selectedTrackId;
      const originalSelectedClipId = this.selectedClipId;
      const undoSnapshot = this.createTimelineHistorySnapshot();
      const clip = this.findClipById(this.selectedClipId);

      if (!clip) {
        this.applyInputError("请先选择要替换的片段。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;

      try {
        const result = await replaceWorkspaceClip(clip.id, { assetId });
        this.applyTimelineResult(result);
        this.applyTimelineEditHistory(undoSnapshot);
        await this.refreshTimelinePreview();
        const replacedClip = this.findClipById(clip.id);
        if (replacedClip) {
          this.selectedTrackId = replacedClip.trackId;
          this.selectedClipId = replacedClip.id;
        }
        return result.timeline;
      } catch (error) {
        this.timeline = originalTimeline;
        this.selectedTrackId = originalSelectedTrackId;
        this.selectedClipId = originalSelectedClipId;
        this.applyRuntimeError(error, "已恢复到操作前时间线。");
        return null;
      }
    },
    async undoTimelineEdit(): Promise<WorkspaceTimelineDto | null> {
      const snapshot = this.timelineUndoSnapshot;
      if (!snapshot) {
        this.applyInputError("当前没有可撤销的时间线编辑。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;
      const redoSnapshot = this.createTimelineHistorySnapshot();

      try {
        const result = await updateWorkspaceTimeline(
          snapshot.timeline.id,
          createWorkspaceTimelineUpdateInput(snapshot.timeline)
        );
        this.applyTimelineResult(result);
        await this.refreshTimelinePreview();
        this.restoreTimelineSnapshotView(snapshot);
        this.applyTimelineHistorySaveState(result, "timeline_undo", "已撤销最近一次时间线编辑。");
        this.timelineRedoSnapshot = redoSnapshot;
        this.timelineUndoSnapshot = null;
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    async redoTimelineEdit(): Promise<WorkspaceTimelineDto | null> {
      const snapshot = this.timelineRedoSnapshot;
      if (!snapshot) {
        this.applyInputError("当前没有可重做的时间线编辑。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.precheck = null;
      const undoSnapshot = this.createTimelineHistorySnapshot();

      try {
        const result = await updateWorkspaceTimeline(
          snapshot.timeline.id,
          createWorkspaceTimelineUpdateInput(snapshot.timeline)
        );
        this.applyTimelineResult(result);
        await this.refreshTimelinePreview();
        this.restoreTimelineSnapshotView(snapshot);
        this.applyTimelineHistorySaveState(result, "timeline_redo", "已重做最近一次时间线编辑。");
        this.timelineUndoSnapshot = undoSnapshot;
        this.timelineRedoSnapshot = null;
        return result.timeline;
      } catch (error) {
        this.applyRuntimeError(error);
        return null;
      }
    },
    applyTimelineResult(result: WorkspaceTimelineResultDto): void {
      this.timeline = result.timeline;
      this.preview = null;
      this.previewError = null;
      this.blockedMessage = result.timeline ? null : result.message;
      this.saveState = result.saveState ?? null;
      this.assemblyState = result.assemblyState ?? null;
      this.lastCommandResult = null;
      this.selectedTrackId = this.resolveSelectedTrackId();
      this.selectedClipId = this.resolveSelectedClipId();
      this.setPlayheadMs(this.playheadMs);
      this.status = result.timeline ? "ready" : "empty";
    },
    createTimelineHistorySnapshot(): WorkspaceTimelineHistorySnapshot | null {
      return createWorkspaceTimelineHistorySnapshot({
        timeline: this.timeline,
        selectedTrackId: this.selectedTrackId,
        selectedClipId: this.selectedClipId,
        playheadMs: this.playheadMs
      });
    },
    applyTimelineEditHistory(snapshot: WorkspaceTimelineHistorySnapshot | null): void {
      this.timelineUndoSnapshot = snapshot;
      this.timelineRedoSnapshot = null;
    },
    clearTimelineHistory(): void {
      this.timelineUndoSnapshot = null;
      this.timelineRedoSnapshot = null;
    },
    restoreTimelineSnapshotView(snapshot: WorkspaceTimelineHistorySnapshot): void {
      this.selectedTrackId = snapshot.selectedTrackId;
      this.selectedClipId = snapshot.selectedClipId;
      this.selectedTrackId = this.resolveSelectedTrackId();
      this.selectedClipId = this.resolveSelectedClipId();
      this.setPlayheadMs(snapshot.playheadMs);
    },
    applyTimelineHistorySaveState(
      result: WorkspaceTimelineResultDto,
      source: "timeline_undo" | "timeline_redo",
      message: string
    ): void {
      this.saveState = createTimelineHistorySaveState(result, source, message);
    },
    async refreshTimelinePreview(): Promise<TimelinePreviewDto | null> {
      if (!this.timeline) {
        this.preview = null;
        this.previewError = null;
        return null;
      }

      const timelineId = this.timeline.id;
      const selectedClipId = this.selectedClipId;
      const requestId = this.previewRequestId + 1;
      this.previewRequestId = requestId;
      const isCurrentPreviewRequest = () =>
        this.previewRequestId === requestId
        && this.timeline?.id === timelineId
        && this.selectedClipId === selectedClipId;

      try {
        const preview = await fetchTimelinePreview(timelineId, { clipId: selectedClipId });
        if (!isCurrentPreviewRequest()) return null;
        this.preview = preview;
        this.previewError = null;
        return preview;
      } catch (error) {
        const runtimeError =
          error instanceof RuntimeRequestError
            ? error
            : new RuntimeRequestError("时间线预览同步失败，请稍后重试。");
        if (!isCurrentPreviewRequest()) return null;
        this.preview = null;
        this.previewError = {
          details: runtimeError.details,
          message: runtimeError.message,
          requestId: runtimeError.requestId,
          status: runtimeError.status
        };
        return null;
      }
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
    selectInsertedAssetClip(assetId: string, startMs: number): void {
      if (!this.timeline) return;
      const clips = this.timeline.tracks.flatMap((track) => track.clips);
      const insertedClip = clips.find(
        (clip) => clip.sourceType === "asset" && clip.sourceId === assetId && clip.startMs === startMs
      ) ?? clips.find((clip) => clip.sourceType === "asset" && clip.sourceId === assetId);
      if (insertedClip) {
        this.selectedTrackId = insertedClip.trackId;
        this.selectedClipId = insertedClip.id;
      }
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
    applyBlockedMessage(message: string): void {
      this.status = "blocked";
      this.error = null;
      this.blockedMessage = message;
      this.lastCommandResult = {
        status: "blocked",
        task: null,
        message
      };
    },
    clearMagicCutBlockedMessage(message?: string): void {
      const targetMessage = message ?? this.blockedMessage ?? this.lastCommandResult?.message ?? "";
      if (!isMagicCutRecoveryMessage(targetMessage)) return;

      if (this.blockedMessage && isMagicCutRecoveryMessage(this.blockedMessage)) {
        this.blockedMessage = null;
      }

      if (
        this.lastCommandResult?.status === "blocked"
        && isMagicCutRecoveryMessage(this.lastCommandResult.message)
      ) {
        this.lastCommandResult = null;
      }

      if (this.status === "blocked") {
        this.status = this.timeline ? "ready" : "empty";
      }
    },
    applyRuntimeError(error: unknown, suffix?: string): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError("AI 剪辑工作台请求失败");
      const message = suffix && !runtimeError.message.endsWith(suffix)
        ? `${runtimeError.message}${resolveRuntimeErrorSuffixSeparator(runtimeError.message)}${suffix}`
        : runtimeError.message;
      this.status = "error";
      this.error = {
        details: runtimeError.details,
        message,
        requestId: runtimeError.requestId,
        status: runtimeError.status
      };
    },
    applyMagicCutSuggestionError(message: string): void {
      this.magicCutSuggestionStatus = "error";
      this.magicCutSuggestionError = {
        details: null,
        message,
        requestId: "",
        status: 0
      };
    }
  }
});

function normalizeCommandTaskStatus(status: string): Exclude<WorkspaceAICommandResultDto["status"], "blocked"> {
  const knownStatuses: TaskStatus[] = ["queued", "running", "cancelling", "succeeded", "failed", "cancelled"];
  return knownStatuses.includes(status as TaskStatus) ? (status as TaskStatus) : "failed";
}

function isMagicCutPrecheckError(error: unknown): error is RuntimeRequestError {
  return (
    error instanceof RuntimeRequestError
    && (
      (
        error.errorCode === "workspace.ai_command_precheck_failed"
        && isMagicCutRecoveryMessage(error.message)
      )
      || (error.status === 400 && isMagicCutRecoveryMessage(error.message))
    )
  );
}

function buildMagicCutUnavailableMessage(message: string): string {
  return message.startsWith("智能粗剪暂不可用：") ? message : `智能粗剪暂不可用：${message}`;
}

function appendCommandTerminalSuggestionLoadFailedMessage(message: string): string {
  const suffix = "建议读取失败，请手动重新读取。";
  const normalizedMessage = message.trim() || "AI 命令状态已更新。";
  if (normalizedMessage.includes(suffix)) return normalizedMessage;
  const separator = normalizedMessage.endsWith("。") ? " " : "。 ";
  return `${normalizedMessage}${separator}${suffix}`;
}

function resolveRuntimeErrorSuffixSeparator(message: string): string {
  return /[。！？.!?]$/.test(message) ? "" : "。";
}

function toRuntimeErrorShape(error: unknown, fallbackMessage: string): RuntimeRequestErrorShape {
  const runtimeError =
    error instanceof RuntimeRequestError
      ? error
      : new RuntimeRequestError(fallbackMessage);
  return {
    details: runtimeError.details,
    errorCode: runtimeError.errorCode || undefined,
    message: runtimeError.message,
    requestId: runtimeError.requestId,
    status: runtimeError.status
  };
}

export function isMagicCutRecoveryMessage(message: string): boolean {
  const normalizedMessage = normalizeMagicCutRecoveryMessage(message);
  return (
    normalizedMessage === "当前 AI 能力已停用。"
    || normalizedMessage.startsWith("智能粗剪能力未启用")
    || normalizedMessage.startsWith("智能粗剪 Provider")
    || normalizedMessage.includes("当前模型不支持智能粗剪")
  );
}

function normalizeMagicCutRecoveryMessage(message: string): string {
  const prefix = "智能粗剪暂不可用：";
  return message.startsWith(prefix) ? message.slice(prefix.length) : message;
}
