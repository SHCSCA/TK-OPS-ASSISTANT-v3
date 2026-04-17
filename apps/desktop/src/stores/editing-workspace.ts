import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  createWorkspaceTimeline,
  fetchWorkspaceTimeline,
  runWorkspaceAICommand,
  updateWorkspaceTimeline
} from "@/app/runtime-client";
import type {
  RuntimeRequestErrorShape,
  WorkspaceAICommandResultDto,
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

type EditingWorkspaceState = {
  blockedMessage: string | null;
  error: RuntimeRequestErrorShape | null;
  lastCommandResult: WorkspaceAICommandResultDto | null;
  projectId: string;
  selectedClipId: string | null;
  selectedTrackId: string | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
};

export const useEditingWorkspaceStore = defineStore("editing-workspace", {
  state: (): EditingWorkspaceState => ({
    blockedMessage: null,
    error: null,
    lastCommandResult: null,
    projectId: "",
    selectedClipId: null,
    selectedTrackId: null,
    status: "idle",
    timeline: null
  }),
  getters: {
    hasTimeline: (state): boolean => state.timeline !== null,
    orderedTracks: (state): WorkspaceTimelineTrackDto[] =>
      [...(state.timeline?.tracks ?? [])].sort((a, b) => a.orderIndex - b.orderIndex),
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

      try {
        this.applyTimelineResult(await fetchWorkspaceTimeline(projectId));
      } catch (error) {
        this.applyRuntimeError(error);
      }
    },
    async createDraft(projectId = this.projectId, name = "主时间线"): Promise<WorkspaceTimelineDto | null> {
      if (!projectId) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.projectId = projectId;

      try {
        const result = await createWorkspaceTimeline(projectId, { name });
        this.applyTimelineResult(result);
        return result.timeline;
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
    async runMagicCut(projectId = this.projectId): Promise<WorkspaceAICommandResultDto | null> {
      if (!projectId) {
        this.applyInputError("请先选择项目。");
        return null;
      }

      this.status = "saving";
      this.error = null;
      this.projectId = projectId;

      try {
        const result = await runWorkspaceAICommand(projectId, {
          timelineId: this.timeline?.id ?? null,
          capabilityId: "magic_cut",
          parameters: {
            selectedTrackId: this.selectedTrackId,
            selectedClipId: this.selectedClipId
          }
        });
        this.lastCommandResult = result;
        this.blockedMessage = result.message;
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
    applyTimelineResult(result: WorkspaceTimelineResultDto): void {
      this.timeline = result.timeline;
      this.blockedMessage = result.timeline ? null : result.message;
      this.selectedTrackId = this.resolveSelectedTrackId();
      this.selectedClipId = this.resolveSelectedClipId();
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
