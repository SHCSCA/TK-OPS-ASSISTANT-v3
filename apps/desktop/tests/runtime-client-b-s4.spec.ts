import { afterEach, describe, expect, it, vi } from "vitest";

import { createRouteAwareFetch, okJsonResponse } from "./runtime-helpers";

describe("B-S4 Runtime client contract", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses canonical B-S4 routes and request shapes", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method, init) => {
        calls.push({
          path,
          method,
          body: init?.body ? JSON.parse(String(init.body)) : undefined
        });
        return okJsonResponse(sampleResponse(path, method));
      })
    );

    const runtimeClient = await import("@/app/runtime-client");

    await runtimeClient.fetchWorkspaceClip("clip-1");
    await runtimeClient.moveWorkspaceClip("clip-1", { targetTrackId: "track-2", startMs: 1800 });
    await runtimeClient.trimWorkspaceClip("clip-1", { inPointMs: 120, durationMs: 3400 });
    await runtimeClient.replaceWorkspaceClip("clip-1", { assetId: "asset-9" });
    await runtimeClient.fetchTimelinePreview("timeline-1");
    await runtimeClient.precheckTimeline("timeline-1");
    await runtimeClient.createVoiceProfile({
      provider: "openai",
      voiceId: "alloy",
      displayName: "标准女声",
      locale: "zh-CN",
      tags: ["default"],
      enabled: true
    });
    await runtimeClient.regenerateVoiceSegment("track-1", "segment-2", {
      instructions: "更有活力"
    });
    await runtimeClient.fetchVoiceWaveform("track-1");
    await runtimeClient.alignSubtitleTrack("track-1", {
      segments: [{ segmentIndex: 0, startMs: 100, endMs: 800 }]
    });
    await runtimeClient.listSubtitleStyleTemplates();
    await runtimeClient.exportSubtitleTrack("track-1", "srt");
    await runtimeClient.listRenderTemplates();
    await runtimeClient.fetchRenderResourceUsage();

    expect(calls).toEqual([
      { path: "/api/workspace/clips/clip-1", method: "GET", body: undefined },
      {
        path: "/api/workspace/clips/clip-1/move",
        method: "POST",
        body: { targetTrackId: "track-2", startMs: 1800 }
      },
      {
        path: "/api/workspace/clips/clip-1/trim",
        method: "POST",
        body: { inPointMs: 120, durationMs: 3400 }
      },
      {
        path: "/api/workspace/clips/clip-1/replace",
        method: "POST",
        body: { assetId: "asset-9" }
      },
      {
        path: "/api/workspace/timelines/timeline-1/preview",
        method: "GET",
        body: undefined
      },
      {
        path: "/api/workspace/timelines/timeline-1/precheck",
        method: "POST",
        body: undefined
      },
      {
        path: "/api/voice/profiles",
        method: "POST",
        body: {
          provider: "openai",
          voiceId: "alloy",
          displayName: "标准女声",
          locale: "zh-CN",
          tags: ["default"],
          enabled: true
        }
      },
      {
        path: "/api/voice/tracks/track-1/segments/segment-2/regenerate",
        method: "POST",
        body: { instructions: "更有活力" }
      },
      { path: "/api/voice/tracks/track-1/waveform", method: "GET", body: undefined },
      {
        path: "/api/subtitles/tracks/track-1/align",
        method: "POST",
        body: { segments: [{ segmentIndex: 0, startMs: 100, endMs: 800 }] }
      },
      { path: "/api/subtitles/style-templates", method: "GET", body: undefined },
      {
        path: "/api/subtitles/tracks/track-1/export",
        method: "POST",
        body: { format: "srt" }
      },
      { path: "/api/renders/templates", method: "GET", body: undefined },
      { path: "/api/renders/resource-usage", method: "GET", body: undefined }
    ]);
  });
});

function sampleResponse(path: string, method: string): unknown {
  if (path.startsWith("/api/workspace/clips/")) {
    if (path.endsWith("/move") || path.endsWith("/trim") || path.endsWith("/replace")) {
      return {
        timeline: {
          id: "timeline-1",
          projectId: "project-1",
          name: "主时间线",
          status: "draft",
          durationSeconds: 12,
          source: "manual",
          tracks: [],
          createdAt: "2026-04-17T12:00:00Z",
          updatedAt: "2026-04-17T12:00:00Z"
        },
        message: "已更新时间线"
      };
    }
    return {
      id: "clip-1",
      label: "镜头 1",
      trackId: "track-1",
      sourceType: "asset",
      sourceId: "asset-1",
      startMs: 0,
      durationMs: 2000,
      inPointMs: 0,
      outPointMs: 2000,
      status: "ready"
    };
  }
  if (path.endsWith("/preview")) {
    return { status: "ready", previewUrl: "http://127.0.0.1:8000/media/preview.mp4" };
  }
  if (path.endsWith("/precheck")) {
    return { status: "ok", issues: [] };
  }
  if (path === "/api/voice/profiles" && method === "POST") {
    return {
      id: "voice-profile-1",
      provider: "openai",
      voiceId: "alloy",
      displayName: "标准女声",
      locale: "zh-CN",
      tags: ["default"],
      enabled: true
    };
  }
  if (path.includes("/regenerate")) {
    return {
      id: "task-voice-1",
      kind: "ai-voice",
      label: "重生成配音片段",
      status: "queued",
      progressPct: 0,
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:00:00Z"
    };
  }
  if (path.endsWith("/waveform")) {
    return { trackId: "track-1", samples: [0, 0.5, 1] };
  }
  if (path.endsWith("/align")) {
    return {
      id: "subtitle-1",
      projectId: "project-1",
      timelineId: null,
      source: "manual",
      language: "zh-CN",
      style: {
        preset: "default",
        fontSize: 40,
        position: "bottom",
        textColor: "#ffffff",
        background: "#000000"
      },
      segments: [],
      status: "ready",
      createdAt: "2026-04-17T12:00:00Z",
      updatedAt: "2026-04-17T12:02:00Z",
      sourceVoice: {
        trackId: "voice-track-1",
        revision: 2,
        updatedAt: "2026-04-17T12:01:00Z"
      },
      alignment: {
        status: "aligned",
        diffSummary: {
          segmentCountChanged: false,
          timingChangedSegments: 1,
          textChangedSegments: 0,
          lockedSegments: 0
        },
        errorCode: null,
        errorMessage: null,
        nextAction: null,
        updatedAt: "2026-04-17T12:02:00Z"
      }
    };
  }
  if (path === "/api/subtitles/style-templates") {
    return [
      {
        id: "subtitle-style-1",
        name: "默认模板",
        description: "适合短视频口播的底部字幕。",
        style: {
          preset: "creator-default",
          fontSize: 32,
          position: "bottom",
          textColor: "#FFFFFF",
          background: "rgba(0,0,0,0.62)"
        }
      }
    ];
  }
  if (path.endsWith("/export")) {
    return {
      trackId: "track-1",
      format: "srt",
      fileName: "track-1.srt",
      content: "1\n00:00:00,100 --> 00:00:00,800\n第一段脚本\n",
      lineCount: 3,
      status: "ready",
      message: "字幕文件已生成。"
    };
  }
  if (path === "/api/renders/templates") {
    return [
      {
        id: "profile-1",
        name: "竖屏标准模板",
        container: "mp4",
        resolution: "1080x1920",
        fps: 30,
        bitrate: "8M",
        audioCodec: "aac",
        videoCodec: "h264",
        createdAt: "2026-04-17T12:00:00Z",
        updatedAt: "2026-04-17T12:00:00Z"
      }
    ];
  }
  if (path === "/api/renders/resource-usage") {
    return {
      cpu: 12,
      gpu: null,
      disk: {
        freeBytes: 1024,
        totalBytes: 4096,
        usedPct: 75
      },
      collectedAt: "2026-04-17T12:00:00Z"
    };
  }
  return {};
}
