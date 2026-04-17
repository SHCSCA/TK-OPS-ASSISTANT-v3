import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useTaskBusStore } from "@/stores/task-bus";

describe("task bus store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("广播 video.import.stage.progress 时按 videoId 分发并缓存最后事件", () => {
    const store = useTaskBusStore();
    const callback = vi.fn();

    store.subscribe("video-1", callback);
    store._handleMessage(
      JSON.stringify({
        schema_version: 1,
        type: "video.import.stage.progress",
        videoId: "video-1",
        stage: "transcribe",
        progressPct: 45
      })
    );

    expect(callback).toHaveBeenCalledWith(
      expect.objectContaining({
        schema_version: 1,
        type: "video.import.stage.progress",
        videoId: "video-1",
        stage: "transcribe",
        progressPct: 45
      })
    );
    expect(store.lastEvents.get("video-1")).toEqual(
      expect.objectContaining({
        type: "video.import.stage.progress",
        videoId: "video-1"
      })
    );
  });

  it("接收 render.progress 时同步刷新任务状态并保留事件", () => {
    const store = useTaskBusStore();

    store._handleMessage(
      JSON.stringify({
        schema_version: 1,
        type: "render.progress",
        taskId: "render-1",
        projectId: "project-1",
        status: "running",
        progressPct: 62,
        bitrateKbps: 3800,
        outputSec: 9.2,
        message: "正在渲染"
      })
    );

    expect(store.tasks.get("render-1")).toEqual(
      expect.objectContaining({
        id: "render-1",
        status: "running",
        progress: 62,
        progressPct: 62,
        project_id: "project-1",
        projectId: "project-1",
        message: "正在渲染"
      })
    );
    expect(store.lastEvents.get("render-1")).toEqual(
      expect.objectContaining({
        type: "render.progress",
        taskId: "render-1"
      })
    );
  });

  it("接收 script.ai.stream.chunk 时按 jobId 分发", () => {
    const store = useTaskBusStore();
    const callback = vi.fn();

    store.subscribe("job-1", callback);
    store._handleMessage(
      JSON.stringify({
        schema_version: 1,
        type: "script.ai.stream.chunk",
        jobId: "job-1",
        sequence: 1,
        deltaText: "第一句"
      })
    );

    expect(callback).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "script.ai.stream.chunk",
        jobId: "job-1",
        sequence: 1,
        deltaText: "第一句"
      })
    );
    expect(store.lastEvents.get("job-1")).toEqual(
      expect.objectContaining({
        type: "script.ai.stream.chunk",
        jobId: "job-1"
      })
    );
  });
});
