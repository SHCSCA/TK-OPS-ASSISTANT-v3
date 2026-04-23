import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  deleteImportedVideo,
  fetchImportedVideos,
  importVideo,
  applyVideoExtractionToProject,
  fetchVideoStages,
  rerunVideoStage
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import { useProjectStore } from "@/stores/project";
import type { TaskEvent, TaskInfo } from "@/types/task-events";
import type { RuntimeRequestErrorShape, VideoStageDto } from "@/types/runtime";
import type { ImportedVideo } from "@/types/video";

export type VideoImportStatus = "idle" | "loading" | "ready" | "importing" | "error" | "applying";

type VideoImportState = {
  error: RuntimeRequestErrorShape | null;
  status: VideoImportStatus;
  taskSnapshots: Record<string, TaskInfo>;
  videos: ImportedVideo[];
  videoStages: Record<string, VideoStageDto[]>;
  _taskUnsubscribers: Record<string, () => void>;
};

export const useVideoImportStore = defineStore("video-import", {
  state: (): VideoImportState => ({
    error: null,
    status: "idle",
    taskSnapshots: {},
    videos: [],
    videoStages: {},
    _taskUnsubscribers: {}
  }),
  actions: {
    initializeWebSocket(): void {
      useTaskBusStore().connect();
      this.syncTaskSnapshots();
    },
    async loadVideos(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        this.videos = await fetchImportedVideos(projectId);
        this.syncTaskSnapshots();
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error, "加载视频列表失败。");
      }
    },
    async loadVideoStages(videoId: string): Promise<void> {
      try {
        const stages = await fetchVideoStages(videoId);
        this.videoStages = {
          ...this.videoStages,
          [videoId]: stages
        };
      } catch (error) {
        console.error(`Failed to load stages for video ${videoId}:`, error);
      }
    },
    async rerunStage(videoId: string, stageId: string): Promise<void> {
      this.error = null;
      try {
        // FIX: Match backend rerun signature if needed, or stick to runtime-client
        await rerunVideoStage(videoId, stageId);
        await this.loadVideoStages(videoId);
      } catch (error) {
        this.applyRuntimeError(error, `重试阶段 ${stageId} 失败。`);
      }
    },
    async importVideoFile(projectId: string, filePath: string): Promise<ImportedVideo | null> {
      this.status = "importing";
      this.error = null;

      try {
        const video = await importVideo(projectId, filePath);
        this.videos = [video, ...this.videos.filter((item) => item.id !== video.id)];
        this.syncTaskSnapshots();
        this.watchVideoTask(projectId, video.id);
        this.status = "ready";
        return video;
      } catch (error) {
        this.applyRuntimeError(error, "导入视频失败。");
        return null;
      }
    },
    async applyExtraction(videoId: string): Promise<void> {
      this.status = "applying";
      this.error = null;

      try {
        const extractionId = `extraction-${videoId}`;
        await applyVideoExtractionToProject(extractionId);
        
        const projectStore = useProjectStore();
        if (projectStore.currentProject) {
          await projectStore.load();
        }
        
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error, "应用视频提取结果失败。");
      }
    },
    async reScanRuntime(): Promise<void> {
      this.status = "loading";
      this.error = null;
      try {
        const projectStore = useProjectStore();
        const projectId = projectStore.currentProject?.projectId;
        if (projectId) {
          await this.loadVideos(projectId);
        }
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error, "重新扫描 Runtime 失败。");
      }
    },
    async removeVideo(videoId: string): Promise<void> {
      this.error = null;

      try {
        await deleteImportedVideo(videoId);
        this.unwatchVideoTask(videoId);
        this.videos = this.videos.filter((item) => item.id !== videoId);
        this.syncTaskSnapshot(videoId);
      } catch (error) {
        this.applyRuntimeError(error, "删除视频失败。");
      }
    },
    taskForVideo(videoId: string): TaskInfo | undefined {
      const snapshot = this.taskSnapshots[videoId];
      if (snapshot) {
        return snapshot;
      }

      const taskBusStore = useTaskBusStore();
      const task = taskBusStore.tasks.get(videoId);
      if (task) {
        return task;
      }

      const lastEvent = taskBusStore.lastEvents?.get(videoId);
      return lastEvent ? deriveTaskInfoFromVideoEvent(videoId, lastEvent) : undefined;
    },
    watchVideoTask(projectId: string, videoId: string): void {
      this.unwatchVideoTask(videoId);
      this.syncTaskSnapshot(videoId);
      this._taskUnsubscribers[videoId] = useTaskBusStore().subscribe(
        videoId,
        (event: TaskEvent) => {
          this.syncTaskSnapshot(videoId, event);
          if (!shouldRefreshVideoList(event)) {
            return;
          }

          void this.loadVideos(projectId);
        }
      );
    },
    unwatchVideoTask(videoId: string): void {
      const unsubscribe = this._taskUnsubscribers[videoId];
      if (!unsubscribe) {
        return;
      }

      unsubscribe();
      delete this._taskUnsubscribers[videoId];
    },
    syncTaskSnapshots(): void {
      this.videos.forEach((video) => {
        this.syncTaskSnapshot(video.id);
      });
    },
    syncTaskSnapshot(videoId: string, event?: TaskEvent): void {
      const taskBusStore = useTaskBusStore();
      const task =
        taskBusStore.tasks.get(videoId) ??
        (event ? deriveTaskInfoFromVideoEvent(videoId, event) : undefined) ??
        deriveTaskInfoFromVideoEvent(videoId, taskBusStore.lastEvents?.get(videoId));

      if (task) {
        this.taskSnapshots = {
          ...this.taskSnapshots,
          [videoId]: task
        };
        return;
      }

      const nextSnapshots = { ...this.taskSnapshots };
      delete nextSnapshots[videoId];
      this.taskSnapshots = nextSnapshots;
    },
    applyRuntimeError(error: unknown, fallbackMessage: string): void {
      const runtimeError =
        error instanceof RuntimeRequestError
          ? error
          : new RuntimeRequestError(fallbackMessage);

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

function shouldRefreshVideoList(event: TaskEvent): boolean {
  if (
    event.taskType === "video_import" &&
    ["task.completed", "task.failed"].includes(event.type)
  ) {
    return true;
  }

  return ["video.import.stage.completed", "video.import.stage.failed"].includes(event.type);
}

function deriveTaskInfoFromVideoEvent(
  videoId: string,
  event: TaskEvent | undefined
): TaskInfo | undefined {
  if (!event) {
    return undefined;
  }

  if (
    ![
      "video.import.stage.started",
      "video.import.stage.progress",
      "video.import.stage.completed",
      "video.import.stage.failed"
    ].includes(event.type)
  ) {
    return undefined;
  }

  const message =
    event.message ??
    deriveStageMessage(event.stage, event.type, event.errorMessage ?? event.errorCode ?? null);
  const progress =
    typeof event.progressPct === "number"
      ? event.progressPct
      : event.type === "video.import.stage.completed"
        ? 100
        : 0;
  const status =
    event.type === "video.import.stage.failed"
      ? "failed"
      : event.type === "video.import.stage.completed"
        ? "succeeded"
        : "running";
  const timestamp = new Date().toISOString();

  return {
    id: videoId,
    task_type: "video_import",
    project_id: event.projectId ?? null,
    status,
    progress,
    message,
    created_at: timestamp,
    updated_at: timestamp
  };
}

function deriveStageMessage(
  stage: string | undefined,
  eventType: string,
  errorMessage: string | null
): string {
  const label = stageLabel(stage);
  if (eventType === "video.import.stage.failed") {
    return errorMessage ? `${label}失败：${errorMessage}` : `${label}失败`;
  }
  if (eventType === "video.import.stage.completed") {
    return `${label}完成`;
  }
  if (eventType === "video.import.stage.progress") {
    return `正在${label}`;
  }
  return `${label}已开始`;
}

function stageLabel(stage: string | undefined): string {
  switch (stage) {
    case "transcribe":
      return "转写";
    case "segment":
      return "切段";
    case "extract_structure":
      return "结构抽取";
    default:
      return "视频处理";
  }
}
