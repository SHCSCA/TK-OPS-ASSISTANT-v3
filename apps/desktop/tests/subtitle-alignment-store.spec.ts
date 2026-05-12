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

  it("加载 Markdown 脚本文档时只提取可对齐字幕文案", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch({ scriptContent: markdownScriptDocument() }));

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");

    expect(store.paragraphs.map((item) => item.text)).toEqual([
      "plain coffee cup",
      "Same old cup every morning.",
      "Link in bio."
    ]);
    expect(store.sourceText).not.toContain("TikTok短视频脚本");
    expect(store.sourceText).not.toContain("| 项目 | 内容 |");
    expect(store.sourceText).not.toContain("9:16");
  });

  it("生成字幕草稿时保存 blocked 状态和中文说明", async () => {
    vi.stubGlobal("fetch", createSubtitleFetch());

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    const result = await store.generate();

    expect(result?.track.status).toBe("ready");
    expect(result?.track.alignment.status).toBe("draft");
    expect(store.status).toBe("blocked");
    expect(store.viewState).toBe("blocked");
    expect(store.generationResult?.message).toContain("字幕对齐 Provider");
    expect(store.tracks[0].id).toBe("subtitle-2");
    expect(store.selectedTrackId).toBe("subtitle-2");
  });

  it("生成字幕时默认携带最新 ready 配音轨", async () => {
    let generateBody: Record<string, unknown> | null = null;
    vi.stubGlobal(
      "fetch",
      createSubtitleFetch({
        captureGenerateBody: (body) => {
          generateBody = body;
        }
      })
    );

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");

    expect(store.sourceVoiceTrack?.id).toBe("voice-ready");

    await store.generate();

    expect(generateBody?.sourceVoiceTrackId).toBe("voice-ready");
  });

  it("生成字幕时使用脚本文案表格行并清理段号时间前缀", async () => {
    let generateBody: Record<string, unknown> | null = null;
    vi.stubGlobal(
      "fetch",
      createSubtitleFetch({
        scriptContent: legacySegmentPrefixedScript(),
        captureGenerateBody: (body) => {
          generateBody = body;
        }
      })
    );

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");
    await store.generate();

    expect(store.scriptRows).toHaveLength(3);
    expect(generateBody?.sourceText).toBe([
      "This lamp made me cancel my dinner plan.",
      "Now my room feels like a 5-star hotel lounge.",
      "Want this vibe? Drop 'glow' and I'll DM you the link."
    ].join("\n"));
    expect(String(generateBody?.sourceText)).not.toContain("S01 0-5s");
    expect(String(generateBody?.sourceText)).not.toContain("Wall Lamp That Changes");
  });

  it("加载旧字幕轨道时按脚本文案表格修正脏段落", async () => {
    vi.stubGlobal(
      "fetch",
      createSubtitleFetch({
        scriptContent: legacySegmentPrefixedScript(),
        legacyMalformedTrack: true
      })
    );

    const store = useSubtitleAlignmentStore();
    await store.load("project-1");

    expect(store.scriptRows).toHaveLength(3);
    expect(store.draftSegments.map((segment) => segment.text)).toEqual([
      "This lamp made me cancel my dinner plan.",
      "Now my room feels like a 5-star hotel lounge.",
      "Want this vibe? Drop 'glow' and I'll DM you the link."
    ]);
    expect(store.selectedTrack?.segments).toHaveLength(3);
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
        if (path === "/api/voice/projects/project-1/tracks") return okJsonResponse([voiceTrack()]);
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
  options: {
    emptyScript?: boolean;
    noTracks?: boolean;
    scriptContent?: string;
    withTrackDetails?: boolean;
    captureGenerateBody?: (body: Record<string, unknown>) => void;
    legacyMalformedTrack?: boolean;
  } = {}
) {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/scripts/projects/project-1/document" && method === "GET") {
      return okJsonResponse(
        scriptDocument(options.emptyScript ? "" : options.scriptContent ?? "第一段脚本\n\n第二段脚本")
      );
    }
    if (path === "/api/subtitles/projects/project-1/tracks") {
      return okJsonResponse(options.noTracks ? [] : [options.legacyMalformedTrack ? legacyMalformedSubtitleTrack() : subtitleTrack()]);
    }
    if (path === "/api/voice/projects/project-1/tracks") {
      return okJsonResponse([voiceTrack("voice-draft", "processing"), voiceTrack("voice-ready", "ready")]);
    }
    if (path === "/api/subtitles/tracks/subtitle-1" && method === "GET") {
      return okJsonResponse(
        options.legacyMalformedTrack
          ? legacyMalformedSubtitleTrack()
          : options.withTrackDetails
            ? subtitleTrackWithDetails("subtitle-1")
            : subtitleTrack()
      );
    }
    if (path === "/api/subtitles/projects/project-1/tracks/generate") {
      options.captureGenerateBody?.(JSON.parse(String(init?.body)));
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

function legacyMalformedSubtitleTrack() {
  return {
    ...subtitleTrack("subtitle-1"),
    segments: [
      "Wall Lamp That Changes Your Mood in Seconds",
      "S01 0-5s This lamp made me cancel my dinner plan.",
      "S02 5-10s Now my room feels like a 5-star hotel lounge.",
      "S03 10-15s Want this vibe?",
      "Drop 'glow' and I'll DM you the link.",
      "This lamp made me cancel my dinner plan. Now my room feels like a 5-star hotel lounge. Want this vibe?",
      "Drop 'glow' and I'll DM you the link."
    ].map((text, index) => ({
      segmentIndex: index,
      text,
      startMs: index * 5000,
      endMs: index * 5000 + 5000,
      confidence: null,
      locked: false
    }))
  };
}

function voiceTrack(id = "voice-ready", status = "ready") {
  return {
    id,
    projectId: "project-1",
    timelineId: null,
    source: "tts",
    provider: "volcengine_tts",
    voiceName: "Vivi 2.0",
    filePath: "voice.mp3",
    segments: [
      {
        segmentIndex: 0,
        text: "第一段脚本",
        startMs: 0,
        endMs: 1800,
        audioAssetId: null,
        regeneration: null
      }
    ],
    status,
    version: {
      revision: 1,
      updatedAt: now()
    },
    config: {
      parameterSource: "profile",
      profileId: "voice-profile-1",
      provider: "volcengine_tts",
      voiceId: "zh_female_vv_uranus_bigtts",
      voiceName: "Vivi 2.0",
      locale: "zh-CN",
      model: "seed-tts-2.0",
      speed: 1,
      pitch: 0,
      emotion: "calm",
      sourceText: "第一段脚本",
      sourceLineCount: 1,
      lastOperation: null
    },
    preview: {
      status: "ready",
      resourceId: id,
      filePath: "voice.mp3",
      message: "音频已生成。"
    },
    activeTask: null,
    createdAt: now(),
    updatedAt: now()
  };
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

function markdownScriptDocument() {
  return `# TikTok短视频脚本

## 1. 脚本元信息

| 项目 | 内容 |
|---|---|
| 平台 | TikTok |
| 视频比例 | 9:16 |
| 建议时长 | 30秒 |

## 5. 分段脚本

| 段落ID | 时间 | 段落目标 | 口播文案 | 屏幕字幕 | 基础画面建议 |
|---|---|---|---|---|---|
| S01 | 0-3秒 | Hook | I thought this was just another plain coffee cup… | plain coffee cup | Hand holds a boring cup. |
| S02 | 3-7秒 | Pain point | You know that feeling? You see the same old cup every morning. | Same old cup every morning. | Person sighs softly. |
| S03 | 25-30秒 | CTA | Tap the link in my bio before they sell out. | Link in bio. | Cup on spring background. |

## 7. 字幕完整稿

\`\`\`text
plain coffee cup
Same old cup every morning.
Link in bio.
\`\`\``;
}

function legacySegmentPrefixedScript() {
  return [
    "Wall Lamp That Changes Your Mood in Seconds",
    "S01 0-5s This lamp made me cancel my dinner plan.",
    "S02 5-10s Now my room feels like a 5-star hotel lounge.",
    "S03 10-15s Want this vibe? Drop 'glow' and I'll DM you the link.",
    "This lamp made me cancel my dinner plan. Now my room feels like a 5-star hotel lounge."
  ].join("\n");
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
