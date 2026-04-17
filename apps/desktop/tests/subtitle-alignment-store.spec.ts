import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSubtitleAlignmentStore } from "@/stores/subtitle-alignment";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M08 字幕对齐中心 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("加载脚本文档和字幕版本后进入 ready 状态", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");

    expect(store.status).toBe("ready");
    expect(store.viewState).toBe("blocked");
    expect(store.paragraphs.map((item) => item.text)).toEqual(["第一段脚本", "第二段脚本"]);
    expect(store.tracks).toHaveLength(1);
    expect(store.selectedTrackId).toBe("subtitle-1");
    expect(store.activeSegmentIndex).toBe(0);
  });

  it("生成字幕草稿时保存 blocked 状态和中文说明", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result?.track.status).toBe("blocked");
    expect(store.status).toBe("blocked");
    expect(store.viewState).toBe("blocked");
    expect(store.generationResult?.message).toContain("字幕对齐 Provider");
    expect(store.tracks[0].id).toBe("subtitle-2");
    expect(store.selectedTrackId).toBe("subtitle-2");
  });

  it("空脚本时不请求生成并进入中文错误态", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch({ emptyScript: true }));

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result).toBeNull();
    expect(store.status).toBe("error");
    expect(store.viewState).toBe("empty");
    expect(store.error?.message).toContain("字幕源文本为空");
  });

  it("没有脚本文本时加载后进入 empty 视图态", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch({ emptyScript: true, noTracks: true }));

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");

    expect(store.status).toBe("empty");
    expect(store.viewState).toBe("empty");
    expect(store.tracks).toEqual([]);
  });

  it("保存手动校正后的字幕段和样式", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    store.updateDraftSegment(0, { text: "校正后的字幕", startMs: 0, endMs: 2200, locked: true });
    store.updateStyle({ fontSize: 38 });
    const updated = await store.updateSelectedTrack();

    expect(updated?.segments[0].text).toBe("校正后的字幕");
    expect(updated?.style.fontSize).toBe(38);
    expect(store.status).toBe("ready");
  });

  it("选择字幕版本时拉取版本详情并同步草稿段", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch({ withTrackDetails: true }));

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    await store.selectTrack("subtitle-1");

    expect(store.selectedTrack?.segments).toHaveLength(2);
    expect(store.draftSegments[1]?.text).toBe("第二段脚本");
  });

  it("删除字幕版本后刷新列表并清空选中态", async () => {
    let tracks = [subtitleTrack("subtitle-1")];
    vi.stubGlobal(
      "fetch",
      createRouteAwareFetch((path, method) => {
        if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
          return okJsonResponse(scriptDocument());
        }
        if (path === "/api/subtitles/projects/project-1/tracks") return okJsonResponse(tracks);
        if (path === "/api/subtitles/tracks/subtitle-1" && method === "DELETE") {
          tracks = [];
          return okJsonResponse(undefined);
        }
        throw new Error(`Unhandled request: ${method} ${path}`);
      })
    );

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    await store.deleteTrack("subtitle-1");

    expect(store.tracks).toEqual([]);
    expect(store.selectedTrackId).toBeNull();
  });
});

function createSubtitleFetch(
  options: { emptyScript?: boolean; noTracks?: boolean; withTrackDetails?: boolean } = {}
) {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(scriptDocument(options.emptyScript ? "" : "第一段脚本\n\n第二段脚本"));
    }
    if (path === "/api/subtitles/projects/project-1/tracks") {
      return okJsonResponse(options.noTracks ? [] : [subtitleTrack()]);
    }
    if (path === "/api/subtitles/tracks/subtitle-1" && method === "GET") {
      return okJsonResponse(
        options.withTrackDetails ? subtitleTrackWithDetails("subtitle-1") : subtitleTrack()
      );
    }
    if (path === "/api/subtitles/projects/project-1/tracks/generate") {
      return okJsonResponse({
        track: subtitleTrack("subtitle-2"),
        task: null,
        message: "尚未配置可用字幕对齐 Provider，已保存字幕草稿。"
      });
    }
    if (path === "/api/subtitles/tracks/subtitle-1" && method === "PATCH") {
      const body = JSON.parse(String(init?.body));
      return okJsonResponse(subtitleTrack("subtitle-1", body.segments[0].text, body.style.fontSize));
    }
    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function scriptDocument(content = "第一段脚本\n\n第二段脚本") {
  return {
    projectId: "project-1",
    currentVersion: {
      revision: 1,
      source: "manual",
      content,
      provider: null,
      model: null,
      aiJobId: null,
      createdAt: now()
    },
    versions: [],
    recentJobs: []
  };
}

function now() {
  return "2026-04-16T10:00:00Z";
}

function subtitleTrack(id = "subtitle-1", text = "第一段脚本", fontSize = 32) {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "script",
    language: "zh-CN",
    style: {
      preset: "creator-default",
      fontSize,
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
    status: "blocked",
    createdAt: now()
  };
}

function subtitleTrackWithDetails(id = "subtitle-1") {
  return {
    ...subtitleTrack(id),
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本",
        startMs: null,
        endMs: null,
        confidence: null,
        locked: false
      },
      {
        segmentIndex: 1,
        text: "第二段脚本",
        startMs: null,
        endMs: null,
        confidence: null,
        locked: false
      }
    ]
  };
}
