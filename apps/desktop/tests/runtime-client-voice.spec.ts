import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  buildVoiceTrackAudioUrl,
  deleteVoiceTrack,
  fetchVoiceProfiles,
  fetchVoiceTrack,
  fetchVoiceTracks,
  generateVoiceTrack
} from "@/app/runtime-client";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M07 配音中心 Runtime client 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("使用稳定 /api/voice 路径、方法和请求体", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });
      if (path === "/api/voice/profiles") return okJsonResponse([voiceProfile()]);
      if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([voiceTrack()]);
      if (path === "/api/voice/projects/project-1/tracks/generate") {
        return okJsonResponse({
          track: voiceTrack("voice-2"),
          task: null,
          message: "尚未配置可用 TTS Provider，已保存配音版本草稿。"
        });
      }
      if (path === "/api/voice/tracks/voice-1" && method === "GET") {
        return okJsonResponse(voiceTrack());
      }
      if (path === "/api/voice/tracks/voice-1" && method === "DELETE") {
        return okJsonResponse(undefined);
      }
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchVoiceProfiles();
    await fetchVoiceTracks("project-1");
    const result = await generateVoiceTrack("project-1", {
      profileId: "alloy-zh",
      sourceText: "第一段",
      speed: 1,
      pitch: 0,
      emotion: "calm"
    });
    await fetchVoiceTrack("voice-1");
    await deleteVoiceTrack("voice-1");

    expect(result.track.status).toBe("blocked");
    expect(calls).toEqual([
      { path: "/api/voice/profiles", method: "GET", body: undefined },
      { path: "/api/voice/projects/project-1/tracks", method: "GET", body: undefined },
      {
        path: "/api/voice/projects/project-1/tracks/generate",
        method: "POST",
        body: {
          profileId: "alloy-zh",
          sourceText: "第一段",
          speed: 1,
          pitch: 0,
          emotion: "calm"
        }
      },
      { path: "/api/voice/tracks/voice-1", method: "GET", body: undefined },
      { path: "/api/voice/tracks/voice-1", method: "DELETE", body: undefined }
    ]);
  });

  it("为播放器生成 Runtime 音频流地址而不是本地文件路径", () => {
    expect(buildVoiceTrackAudioUrl("voice track-1", "2026-05-11T10:00:00Z")).toBe(
      "http://127.0.0.1:8000/api/voice/tracks/voice%20track-1/audio?v=2026-05-11T10%3A00%3A00Z"
    );
  });

  it("把 Runtime 错误信封转换为可见错误", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch(() => errorJsonResponse(400, "脚本文本为空，请先在脚本与选题中心创建内容。"))
    );

    await expect(fetchVoiceProfiles()).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "脚本文本为空，请先在脚本与选题中心创建内容。",
      status: 400
    } satisfies Partial<RuntimeRequestError>);
  });
});

function now() {
  return "2026-04-16T10:00:00Z";
}

function voiceProfile() {
  return {
    id: "alloy-zh",
    provider: "pending_provider",
    voiceId: "alloy",
    displayName: "清晰叙述",
    locale: "zh-CN",
    tags: ["清晰", "旁白"],
    enabled: true
  };
}

function voiceTrack(id = "voice-1") {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "tts",
    provider: "pending_provider",
    voiceName: "清晰叙述",
    filePath: null,
    segments: [
      {
        segmentIndex: 0,
        text: "第一段",
        startMs: null,
        endMs: null,
        audioAssetId: null
      }
    ],
    status: "blocked",
    createdAt: now()
  };
}
