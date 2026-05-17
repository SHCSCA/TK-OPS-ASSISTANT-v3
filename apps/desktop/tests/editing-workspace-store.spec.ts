import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useEditingWorkspaceStore } from "@/stores/editing-workspace";

import { createRouteAwareFetch, errorJsonResponse, okJsonResponse } from "./runtime-helpers";

describe("M05 AI 剪辑工作台 store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("加载没有时间线的项目后进入 empty 状态", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ timeline: null }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.status).toBe("empty");
    expect(store.timeline).toBeNull();
    expect(store.blockedMessage).toBe("当前项目还没有时间线草稿。");
  });

  it("创建时间线草稿后进入 ready 并保存真实时间线", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ timeline: null }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const created = await store.createDraft("project-1");

    expect(store.status).toBe("ready");
    expect(created?.id).toBe("timeline-1");
    expect(store.timeline?.tracks).toEqual([]);
    expect(store.blockedMessage).toBeNull();
  });

  it("load 同步读取当前项目资产", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({
      assets: [
        asset("asset-project", "project-1"),
        asset("asset-source", null, "project-1"),
        asset("asset-other", "project-2")
      ]
    }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.status).toBe("ready");
    expect(store.assetStatus).toBe("ready");
    expect(store.assets.map((item) => item.id)).toEqual(["asset-project", "asset-source"]);
    expect(store.assetError).toBeNull();
  });

  it("loadAssets 无参数时清空资产且不回退到当前项目", async () => {
    const fetchMock = createWorkspaceFetch({
      assets: [asset("asset-project", "project-1")]
    });
    vi.stubGlobal("fetch", fetchMock);

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    expect(store.projectId).toBe("project-1");
    expect(store.assets.map((item) => item.id)).toEqual(["asset-project"]);

    fetchMock.mockClear();
    const assets = await store.loadAssets();

    expect(assets).toEqual([]);
    expect(store.assets).toEqual([]);
    expect(store.assetStatus).toBe("idle");
    expect(store.assetError).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("保存轨道时保留时间线并回到 ready 状态", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    store.timeline!.tracks = [videoTrack()];

    const saved = await store.saveTimeline();

    expect(saved?.tracks[0].name).toBe("主画面");
    expect(store.status).toBe("ready");
    expect(store.timeline?.tracks[0].kind).toBe("video");
  });

  it("汇入工作台时间线后保存来源状态并选中首条受管轨道", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const timelineResult = await store.assembleTimeline("project-1");

    expect(timelineResult?.tracks[0].id).toBe("managed-video-storyboard");
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.saveState?.source).toBe("assembly");
    expect(store.assemblyState?.sources.map((source) => source.kind)).toEqual([
      "script",
      "storyboard",
      "voice",
      "subtitle"
    ]);
  });

  it("删除选中片段后刷新时间线并保留受管轨道选择", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.deleteSelectedClip();

    expect(timelineResult?.tracks[0].clips).toEqual([]);
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBeNull();
    expect(store.saveState?.source).toBe("clip_delete");
  });

  it("分割选中片段时使用当前播放头并保留左半段选中", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectClip("managed-video-storyboard-01");
    store.setPlayheadMs(3000);

    const timelineResult = await store.splitSelectedClip();

    const clips = timelineResult?.tracks[0].clips ?? [];
    expect(clips.map((clip) => clip.id)).toEqual([
      "managed-video-storyboard-01",
      "managed-video-storyboard-01-split-3000"
    ]);
    expect(clips[0].durationMs).toBe(3000);
    expect(clips[1].startMs).toBe(3000);
    expect(store.status).toBe("ready");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.saveState?.source).toBe("clip_split");
  });

  it("播放头不在选中片段内部时拒绝分割", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectClip("managed-video-storyboard-01");
    store.setPlayheadMs(5000);

    const result = await store.splitSelectedClip();

    expect(result).toBeNull();
    expect(store.status).toBe("error");
    expect(store.error?.message).toBe("播放头必须位于选中片段内部才能分割。");
  });

  it("按步进移动选中片段时通过 Runtime 保存", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.moveSelectedClipBy(500);

    expect(timelineResult?.tracks[0].clips[0].startMs).toBe(500);
    expect(store.status).toBe("ready");
    expect(store.saveState?.source).toBe("clip_move");
  });

  it("提交拖拽移动预览时通过 Runtime 保存并保留选中片段", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.commitMovePreview({
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 500,
      durationMs: 5000
    });

    expect(timelineResult?.tracks[0].clips[0].startMs).toBe(500);
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.saveState?.source).toBe("clip_move");
  });

  it("提交拖拽移动失败时保留原时间线并显示中文错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failMove: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    const originalTimeline = store.timeline;
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.commitMovePreview({
      gesture: "move",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      startMs: 500,
      durationMs: 5000
    });

    expect(timelineResult).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline).toBe(originalTimeline);
    expect(store.timeline?.tracks[0].clips[0].startMs).toBe(0);
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.error?.message).toBe("目标轨道已锁定，无法移动片段。");
  });

  it("提交左边缘拖拽裁剪预览时通过 Runtime 保存并保留选中片段", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.commitTrimPreview({
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "left",
      startMs: 500,
      durationMs: 4500,
      inPointMs: 500
    });

    expect(timelineResult?.tracks[0].clips[0]).toMatchObject({
      startMs: 500,
      durationMs: 4500,
      inPointMs: 500
    });
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.saveState?.source).toBe("clip_trim");
  });

  it("提交右边缘拖拽裁剪预览时只提交新时长", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.commitTrimPreview({
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "right",
      startMs: 0,
      durationMs: 4200,
      inPointMs: 0
    });

    expect(timelineResult?.tracks[0].clips[0].durationMs).toBe(4200);
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.saveState?.source).toBe("clip_trim");
  });

  it("提交拖拽裁剪失败时回滚时间线和选择并显示中文错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failTrim: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    const originalTimeline = store.timeline;
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.commitTrimPreview({
      gesture: "trim",
      clipId: "managed-video-storyboard-01",
      trackId: "managed-video-storyboard",
      edge: "left",
      startMs: 500,
      durationMs: 100,
      inPointMs: 500
    });

    expect(timelineResult).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline).toBe(originalTimeline);
    expect(store.timeline?.tracks[0].clips[0].startMs).toBe(0);
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.error?.message).toBe("片段裁剪后至少需要保留 500ms。");
  });

  it("按右边缘裁剪选中片段时通过 Runtime 保存", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.trimSelectedClip("right", -500);

    expect(timelineResult?.tracks[0].clips[0].durationMs).toBe(4500);
    expect(store.status).toBe("ready");
    expect(store.saveState?.source).toBe("clip_trim");
  });

  it("按播放头把资产加入时间线并选中新资产片段", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    store.setPlayheadMs(2500);

    const timelineResult = await store.insertAssetAtPlayhead("asset-1");

    expect(timelineResult?.tracks[0].clips[0]).toMatchObject({
      id: "asset-clip-1",
      sourceType: "asset",
      sourceId: "asset-1",
      startMs: 2500
    });
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("track-video");
    expect(store.selectedClipId).toBe("asset-clip-1");
    expect(store.saveState?.source).toBe("clip_insert_asset");
  });

  it("资产加入失败时保留原时间线并显示中文错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failInsert: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const originalTimeline = store.timeline;
    store.setPlayheadMs(2500);

    const timelineResult = await store.insertAssetAtPlayhead("asset-1");

    expect(timelineResult).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline).toBe(originalTimeline);
    expect(store.error?.message).toBe("资产入轨失败，请检查素材状态。");
  });

  it("用资产替换选中片段后保留选中片段", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.replaceSelectedClipWithAsset("asset-1");

    expect(timelineResult?.tracks[0].clips[0]).toMatchObject({
      id: "managed-video-storyboard-01",
      sourceType: "asset",
      sourceId: "asset-1"
    });
    expect(store.status).toBe("ready");
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.saveState?.source).toBe("clip_replace");
  });

  it("资产替换失败时回滚时间线和选择并显示中文错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failReplace: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    await store.assembleTimeline("project-1");
    const originalTimeline = store.timeline;
    store.selectTrack("managed-video-storyboard");
    store.selectClip("managed-video-storyboard-01");

    const timelineResult = await store.replaceSelectedClipWithAsset("asset-1");

    expect(timelineResult).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline).toBe(originalTimeline);
    expect(store.selectedTrackId).toBe("managed-video-storyboard");
    expect(store.selectedClipId).toBe("managed-video-storyboard-01");
    expect(store.error?.message).toBe("资产替换失败，请检查素材状态。");
  });

  it("执行时间线预检后保存真实预检结果", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const precheck = await store.runPrecheck();

    expect(precheck?.status).toBe("ready");
    expect(store.precheck?.issues).toEqual([]);
    expect(store.status).toBe("ready");
  });

  it("AI 魔法剪被阻断时保存 blockedMessage", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch());

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const result = await store.runMagicCut("project-1");

    expect(result?.status).toBe("blocked");
    expect(store.status).toBe("blocked");
    expect(store.blockedMessage).toContain("AI 剪辑命令尚未接入 Provider");
  });

  it("AI 魔法剪进入队列时不写入阻断警告", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({
      aiCommandResult: {
        status: "queued",
        task: {
          taskId: "task-workspace-1",
          taskType: "ai-workspace-command",
          projectId: "project-1",
          status: "queued",
          progress: 0,
          message: "AI 命令 magic_cut 已进入任务队列。"
        },
        message: "AI 命令已进入任务队列，正在通过 TaskBus 处理。"
      }
    }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    const result = await store.runMagicCut("project-1");

    expect(result?.status).toBe("queued");
    expect(store.status).toBe("ready");
    expect(store.blockedMessage).toBeNull();
    expect(store.lastCommandResult?.message).toBe("AI 命令已进入任务队列，正在通过 TaskBus 处理。");
  });

  it("Runtime 保存失败时进入 error 并保留既有草稿", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failSave: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");
    store.timeline!.tracks = [videoTrack()];
    const saved = await store.saveTimeline();

    expect(saved).toBeNull();
    expect(store.status).toBe("error");
    expect(store.timeline?.id).toBe("timeline-1");
    expect(store.error?.message).toBe("时间线保存失败，请稍后重试。");
  });

  it("资产读取失败时保留时间线和 ready 状态，只设置资产错误", async () => {
    vi.stubGlobal("fetch", createWorkspaceFetch({ failAssets: true }));

    const store = useEditingWorkspaceStore();
    await store.load("project-1");

    expect(store.status).toBe("ready");
    expect(store.timeline?.id).toBe("timeline-1");
    expect(store.assetStatus).toBe("error");
    expect(store.assetError?.message).toBe("资产读取失败，请稍后重试。");
    expect(store.assets).toEqual([]);
  });
});

function createWorkspaceFetch(
  options: {
    assets?: ReturnType<typeof asset>[];
    aiCommandResult?: {
      message: string;
      status: "blocked" | "queued";
      task: Record<string, unknown> | null;
    };
    failAssets?: boolean;
    failInsert?: boolean;
    failMove?: boolean;
    failReplace?: boolean;
    failSave?: boolean;
    failTrim?: boolean;
    timeline?: ReturnType<typeof timeline> | null;
  } = {}
) {
  return createRouteAwareFetch((path, method, init) => {
    if (path === "/api/assets" && method === "GET") {
      if (options.failAssets) {
        return errorJsonResponse(500, "资产读取失败，请稍后重试。");
      }
      return okJsonResponse(options.assets ?? [asset("asset-1", "project-1")]);
    }

    if (path === "/api/workspace/projects/project-1/timeline" && method === "GET") {
      return okJsonResponse({
        timeline: options.timeline === undefined ? timeline() : options.timeline,
        message:
          options.timeline === null
            ? "当前项目还没有时间线草稿。"
            : "已加载时间线草稿。"
      });
    }

    if (path === "/api/workspace/projects/project-1/timeline" && method === "POST") {
      return okJsonResponse({
        timeline: timeline(),
        message: "已创建时间线草稿。"
      }, 201);
    }

    if (path === "/api/workspace/timelines/timeline-1" && method === "PATCH") {
      if (options.failSave) {
        return errorJsonResponse(500, "时间线保存失败，请稍后重试。");
      }
      const body = JSON.parse(String(init?.body));
      return okJsonResponse({
        timeline: timeline("timeline-1", body.tracks),
        message: "已保存时间线草稿。"
      });
    }

    if (path === "/api/workspace/projects/project-1/timeline/assemble" && method === "POST") {
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack()]),
        activeTask: null,
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "assembly",
          message: "已保存 M05 剪辑工作台受管轨道。"
        },
        assemblyState: {
          status: "ready",
          sources: [
            sourceState("script"),
            sourceState("storyboard"),
            sourceState("voice"),
            sourceState("subtitle")
          ],
          issues: []
        },
        message: "剪辑工作台时间线已从脚本、分镜、配音和字幕汇入。"
      });
    }

    if (path === "/api/workspace/clips/managed-video-storyboard-01" && method === "DELETE") {
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack([])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_delete",
          message: "已确认删除选中片段。"
        },
        message: "片段已删除。"
      });
    }

    if (path === "/api/workspace/clips/managed-video-storyboard-01/move" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      expect(body).toEqual({ targetTrackId: "managed-video-storyboard", startMs: 500 });
      if (options.failMove) {
        return errorJsonResponse(409, "目标轨道已锁定，无法移动片段。");
      }
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack([
          managedVideoClip({ startMs: 500 })
        ])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_move",
          message: "已确认保存片段位置变更。"
        },
        message: "片段已移动。"
      });
    }

    if (path === "/api/workspace/clips/managed-video-storyboard-01/trim" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      if (options.failTrim) {
        return errorJsonResponse(400, "片段裁剪后至少需要保留 500ms。");
      }

      if (body.startMs !== undefined) {
        expect(body).toEqual({ startMs: 500, durationMs: 4500, inPointMs: 500 });
        return okJsonResponse({
          timeline: timeline("timeline-1", [managedVideoTrack([
            managedVideoClip({ startMs: 500, durationMs: 4500, inPointMs: 500 })
          ])]),
          saveState: {
            saved: true,
            updatedAt: now(),
            source: "clip_trim",
            message: "已确认保存片段裁剪结果。"
          },
          message: "片段已裁剪。"
        });
      }

      if (body.durationMs === 4200) {
        return okJsonResponse({
          timeline: timeline("timeline-1", [managedVideoTrack([
            managedVideoClip({ durationMs: 4200 })
          ])]),
          saveState: {
            saved: true,
            updatedAt: now(),
            source: "clip_trim",
            message: "已确认保存片段裁剪结果。"
          },
          message: "片段已裁剪。"
        });
      }

      expect(body).toEqual({ durationMs: 4500 });
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack([
          managedVideoClip({ durationMs: 4500 })
        ])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_trim",
          message: "已确认保存片段裁剪结果。"
        },
        message: "片段已裁剪。"
      });
    }

    if (path === "/api/workspace/timelines/timeline-1/clips/insert-asset" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      expect(body).toEqual({ assetId: "asset-1", startMs: 2500 });
      if (options.failInsert) {
        return errorJsonResponse(409, "资产入轨失败，请检查素材状态。");
      }
      return okJsonResponse({
        timeline: timeline("timeline-1", [videoTrack([assetClip()])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_insert_asset",
          message: "已确认保存资产入轨结果。"
        },
        message: "资产已加入时间线。"
      });
    }

    if (path === "/api/workspace/clips/managed-video-storyboard-01/replace" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      expect(body).toEqual({ assetId: "asset-1" });
      if (options.failReplace) {
        return errorJsonResponse(409, "资产替换失败，请检查素材状态。");
      }
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack([
          managedVideoClip({
            sourceType: "asset",
            sourceId: "asset-1",
            label: "asset-1"
          })
        ])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_replace",
          message: "已确认保存资产替换结果。"
        },
        message: "片段已替换。"
      });
    }

    if (path === "/api/workspace/clips/managed-video-storyboard-01/split" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      expect(body).toEqual({ splitAtMs: 3000 });
      return okJsonResponse({
        timeline: timeline("timeline-1", [managedVideoTrack([
          managedVideoClip({
            durationMs: 3000,
            outPointMs: 3000
          }),
          managedVideoClip({
            id: "managed-video-storyboard-01-split-3000",
            startMs: 3000,
            durationMs: 2000,
            inPointMs: 3000,
            outPointMs: 5000
          })
        ])]),
        saveState: {
          saved: true,
          updatedAt: now(),
          source: "clip_split",
          message: "已确认保存片段分割结果。"
        },
        message: "片段已分割。"
      });
    }

    if (path === "/api/workspace/timelines/timeline-1/precheck" && method === "POST") {
      return okJsonResponse({
        timelineId: "timeline-1",
        status: "ready",
        message: "时间线本地预检通过。",
        issues: []
      });
    }

    if (path === "/api/workspace/projects/project-1/ai-commands" && method === "POST") {
      return okJsonResponse(options.aiCommandResult ?? {
        status: "blocked",
        task: null,
        message: "AI 剪辑命令尚未接入 Provider，本阶段仅保存时间线草稿。"
      });
    }

    throw new Error(`Unhandled request: ${method} ${path}`);
  });
}

function now() {
  return "2026-04-17T10:00:00Z";
}

function timeline(id = "timeline-1", tracks: unknown[] = []) {
  return {
    id,
    projectId: "project-1",
    name: "AI 剪辑草稿",
    status: "draft",
    durationSeconds: 12,
    source: "manual",
    tracks,
    createdAt: now(),
    updatedAt: now()
  };
}

function asset(id: string, projectId: string | null, sourceProjectId = projectId) {
  return {
    id,
    name: id,
    type: "video",
    source: "local",
    filePath: `G:/fixtures/${id}.mp4`,
    fileSizeBytes: 1024,
    durationMs: 12000,
    thumbnailPath: null,
    tags: null,
    projectId,
    metadataJson: null,
    sourceInfo: {
      source: "local",
      projectId: sourceProjectId,
      groupId: null,
      filePath: `G:/fixtures/${id}.mp4`,
      metadataSummary: {}
    },
    availability: {
      status: "available",
      errorCode: null,
      errorMessage: null,
      nextAction: null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "missing",
      path: null,
      generatedAt: null
    },
    createdAt: now(),
    updatedAt: now()
  };
}

function videoTrack(clips: unknown[] = []) {
  return {
    id: "track-video",
    kind: "video",
    name: "主画面",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function managedVideoTrack(clips = [managedVideoClip()]) {
  return {
    id: "managed-video-storyboard",
    kind: "video",
    name: "分镜视频轨",
    orderIndex: 0,
    locked: false,
    muted: false,
    clips
  };
}

function managedVideoClip(overrides: Partial<ReturnType<typeof managedVideoClip>> = {}) {
  return {
    id: "managed-video-storyboard-01",
    trackId: "managed-video-storyboard",
    sourceType: "storyboard",
    sourceId: "storyboard:1:S01",
    label: "S01 · 分镜画面",
    startMs: 0,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: "pending",
    metadata: {
      sourceKind: "storyboard",
      sourceRevision: 1,
      segmentIndex: 0,
      segmentId: "S01",
      text: "测试字幕",
      visualPrompt: "测试画面"
    },
    ...overrides
  };
}

function assetClip() {
  return {
    id: "asset-clip-1",
    trackId: "track-video",
    sourceType: "asset",
    sourceId: "asset-1",
    label: "asset-1",
    startMs: 2500,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: "ready",
    metadata: {
      sourceKind: "asset",
      sourceRevision: null,
      segmentIndex: null,
      segmentId: null,
      text: null,
      visualPrompt: null
    }
  };
}

function sourceState(kind: string) {
  return {
    kind,
    status: "ready",
    label: kind,
    revision: kind === "script" || kind === "storyboard" ? 1 : null,
    trackId: kind === "voice" || kind === "subtitle" ? `${kind}-track` : null,
    segmentCount: 1,
    message: "已读取。"
  };
}
