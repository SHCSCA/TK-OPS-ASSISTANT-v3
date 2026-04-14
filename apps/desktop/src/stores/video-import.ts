import { defineStore } from "pinia";

import {
  RuntimeRequestError,
  deleteImportedVideo,
  fetchImportedVideos,
  importVideo
} from "@/app/runtime-client";
import type { RuntimeRequestErrorShape } from "@/types/runtime";
import type { ImportedVideo } from "@/types/video";

export type VideoImportStatus = "idle" | "loading" | "ready" | "importing" | "error";

type VideoImportState = {
  error: RuntimeRequestErrorShape | null;
  status: VideoImportStatus;
  videos: ImportedVideo[];
};

export const useVideoImportStore = defineStore("video-import", {
  state: (): VideoImportState => ({
    error: null,
    status: "idle",
    videos: []
  }),
  actions: {
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
        this.videos = this.videos.filter((item) => item.id !== videoId);
      } catch (error) {
        this.applyRuntimeError(error, "删除视频失败。");
      }
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
