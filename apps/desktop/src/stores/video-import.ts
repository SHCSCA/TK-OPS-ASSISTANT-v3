import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  deleteImportedVideo,
  fetchImportedVideos,
  importVideo
} from "@/app/runtime-client";
import { useTaskBusStore } from "@/stores/task-bus";
import type { TaskEvent, TaskInfo } from "@/types/task-events";
import type { RuntimeRequestErrorShape } from "@/types/runtime";
import type { ImportedVideo } from "@/types/video";

export type VideoImportStatus = "idle" | "loading" | "ready" | "importing" | "error";

type VideoImportState = {
  error: RuntimeRequestErrorShape | null;
  status: VideoImportStatus;
  videos: ImportedVideo[];
  _taskUnsubscribers: Record<string, () => void>;
};

export const useVideoImportStore = defineStore("video-import", {
  state: (): VideoImportState => ({
    error: null,
    status: "idle",
    videos: [],
    _taskUnsubscribers: {}
  }),
  actions: {
    initializeWebSocket(): void {
      useTaskBusStore().connect();
    },
    async loadVideos(projectId: string): Promise<void> {
      this.status = "loading";
      this.error = null;

      try {
        this.videos = await fetchImportedVideos(projectId);
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error, "加载视频列表失败。");
      }
    },
    async importVideoFile(projectId: string, filePath: string): Promise<ImportedVideo | null> {
      this.status = "importing";
      this.error = null;

      try {
        const video = await importVideo(projectId, filePath);
        this.videos = [video, ...this.videos.filter((item) => item.id !== video.id)];
        this.watchVideoTask(projectId, video.id);
        this.status = "ready";
        return video;
      } catch (error) {
        this.applyRuntimeError(error, "导入视频失败。");
        return null;
      }
    },
    async removeVideo(videoId: string): Promise<void> {
      this.error = null;

      try {
        await deleteImportedVideo(videoId);
        this.unwatchVideoTask(videoId);
        this.videos = this.videos.filter((item) => item.id !== videoId);
      } catch (error) {
        this.applyRuntimeError(error, "删除视频失败。");
      }
    },
    taskForVideo(videoId: string): TaskInfo | undefined {
      return useTaskBusStore().tasks.get(videoId);
    },
    watchVideoTask(projectId: string, videoId: string): void {
      this.unwatchVideoTask(videoId);
      this._taskUnsubscribers[videoId] = useTaskBusStore().subscribe(
        videoId,
        (event: TaskEvent) => {
          if (
            event.taskType !== "video_import" ||
            !["task.completed", "task.failed"].includes(event.type)
          ) {
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
