import { afterEach, describe, expect, it, vi } from "vitest";

import {
  RuntimeRequestError,
  deleteSubtitleTrack,
  fetchSubtitleTrack,
  fetchSubtitleTracks,
  generateSubtitleTrack,
  updateSubtitleTrack
} from "@/app/runtime-client";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M08 字幕对齐中心 Runtime client 契约", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("使用稳定 /api/subtitles 路径、方法和请求体", async () => {
    const calls: Array<{ body?: unknown; method: string; path: string }> = [];
    const fetchMock = createRouteAwareFetch((path, method, init) => {
      calls.push({
        path,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined
      });
      if (path === "/api/subtitles/projects/project-1/tracks") {
        return okJsonResponse([subtitleTrack()]);
      }
      if (path === "/api/subtitles/projects/project-1/tracks/generate") {
        return okJsonResponse({
          track: subtitleTrack("subtitle-2"),
          task: null,
          message: "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"
        });
      }
      if (path === "/api/subtitles/tracks/subtitle-1" && method === "GET") {
        return okJsonResponse(subtitleTrack());
      }
      if (path === "/api/subtitles/tracks/subtitle-1" && method === "PATCH") {
        return okJsonResponse(subtitleTrack("subtitle-1", "校正后的字幕"));
      }
      if (path === "/api/subtitles/tracks/subtitle-1" && method === "DELETE") {
        return okJsonResponse(undefined);
      }
      throw new Error(`Unhandled request: ${method} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchSubtitleTracks("project-1");
    const result = await generateSubtitleTrack("project-1", {
      sourceText: "第一段脚本",
      language: "zh-CN",
      stylePreset: "creator-default",
      sourceVoiceTrackId: "voice-track-1"
    });
    await fetchSubtitleTrack("subtitle-1");
    await updateSubtitleTrack("subtitle-1", {
      segments: [
        {
          segmentIndex: 0,
          text: "校正后的字幕",
          startMs: 0,
          endMs: 2100,
          confidence: null,
          locked: true
        }
      ],
      style: subtitleTrack().style
    });
    await deleteSubtitleTrack("subtitle-1");

    expect(result.track.status).toBe("ready");
    expect(result.track.alignment.status).toBe("draft");
    expect(calls).toEqual([
      { path: "/api/subtitles/projects/project-1/tracks", method: "GET", body: undefined },
      {
        path: "/api/subtitles/projects/project-1/tracks/generate",
        method: "POST",
        body: {
          sourceText: "第一段脚本",
          language: "zh-CN",
          stylePreset: "creator-default",
          sourceVoiceTrackId: "voice-track-1"
        }
      },
      { path: "/api/subtitles/tracks/subtitle-1", method: "GET", body: undefined },
      {
        path: "/api/subtitles/tracks/subtitle-1",
        method: "PATCH",
        body: {
          segments: [
            {
              segmentIndex: 0,
              text: "校正后的字幕",
              startMs: 0,
              endMs: 2100,
              confidence: null,
              locked: true
            }
          ],
          style: subtitleTrack().style
        }
      },
      { path: "/api/subtitles/tracks/subtitle-1", method: "DELETE", body: undefined }
    ]);
  });

  it("把 Runtime 错误信封转换为可见中文错误", async () => {
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch(() =>
        errorJsonResponse(400, "字幕源文本为空，请先在脚本与选题中心创建内容。")
      )
    );

    await expect(fetchSubtitleTracks("project-1")).rejects.toMatchObject({
      name: "RuntimeRequestError",
      message: "字幕源文本为空，请先在脚本与选题中心创建内容。",
      status: 400
    } satisfies Partial<RuntimeRequestError>);
  });
});

function now() {
  return "2026-04-16T10:00:00Z";
}

function subtitleTrack(id = "subtitle-1", text = "第一段脚本") {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "script",
    language: "zh-CN",
    style: {
      preset: "creator-default",
      fontSize: 32,
      position: "bottom",
      textColor: "#FFFFFF",
      background: "rgba(0,0,0,0.62)"
    },
    segments: [
      {
        segmentIndex: 0,
        text,
        startMs: null,
        endMs: null,
        confidence: null,
        locked: false
      }
    ],
    status: "ready",
    createdAt: now(),
    updatedAt: now(),
    sourceVoice: null,
    alignment: {
      status: "draft",
      diffSummary: null,
      errorCode: null,
      errorMessage: null,
      nextAction: "绑定来源配音轨后重新对齐。",
      updatedAt: now()
    }
  };
}
