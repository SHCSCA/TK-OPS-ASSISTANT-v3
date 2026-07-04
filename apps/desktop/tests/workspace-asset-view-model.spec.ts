import { describe, expect, it } from "vitest";

import {
  buildWorkspaceAssetCards,
  resolveDefaultWorkspaceAssetTab,
  resolveWorkspaceAssetTabFromSourceType,
  sourceTypeLabel
} from "@/modules/workspace/workspaceAssetViewModel";
import type { AssetDto, WorkspaceTimelineDto } from "@/types/runtime";

describe("workspace asset view model", () => {
  it("只返回当前项目关联的资产", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({ id: "asset-direct", projectId: "project-1" }),
        asset({ id: "asset-source", projectId: null, sourceProjectId: "project-1" }),
        asset({ id: "asset-other", projectId: "project-2", sourceProjectId: "project-2" })
      ],
      timeline: timeline([])
    });

    expect(cards.map((card) => card.id)).toEqual(["asset-direct", "asset-source"]);
  });

  it("把已在时间线中的素材标记为已入轨并保留加入轨道操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [asset({ id: "asset-video", projectId: "project-1", type: "video" })],
      timeline: timeline([
        {
          id: "clip-1",
          trackId: "track-video",
          sourceType: "asset",
          sourceId: "asset-video",
          label: "片段",
          startMs: 0,
          durationMs: 5000,
          inPointMs: 0,
          outPointMs: null,
          status: "ready"
        }
      ])
    });

    expect(cards[0]).toMatchObject({
      id: "asset-video",
      isOnTimeline: true,
      status: "已入轨",
      tone: "success",
      primaryAction: "加入轨道"
    });
  });

  it("为未入轨音频素材提供加入音轨操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [asset({ id: "asset-audio", projectId: "project-1", type: "audio" })],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "可用",
      tone: "neutral",
      primaryAction: "加入音轨"
    });
  });

  it("为未入轨非音频可用素材提供加入轨道操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [asset({ id: "asset-image", projectId: "project-1", type: "image" })],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "可用",
      tone: "neutral",
      primaryAction: "加入轨道"
    });
  });

  it("把 Runtime ready 资产视为可用素材", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [asset({ id: "asset-ready", projectId: "project-1", availabilityStatus: "ready" })],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "可用",
      tone: "neutral"
    });
  });

  it("把缺失素材显示为路径缺失并使用重新检查操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({
          id: "asset-missing",
          projectId: "project-1",
          availabilityStatus: "missing",
          nextAction: null
        })
      ],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "路径缺失",
      tone: "danger",
      primaryAction: "重新检查"
    });
  });

  it("缺失素材存在 nextAction 时仍使用统一重新检查操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({
          id: "asset-missing-action",
          projectId: "project-1",
          availabilityStatus: "missing",
          nextAction: "选择新路径"
        })
      ],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "路径缺失",
      tone: "danger",
      primaryAction: "重新检查"
    });
  });

  it("把需转码素材显示为需转码并提供检查操作", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({
          id: "asset-transcode",
          projectId: "project-1",
          availabilityStatus: "needs_transcode"
        })
      ],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      status: "需转码",
      tone: "warning",
      primaryAction: "重新检查"
    });
  });

  it("输出中文来源类型和时长标签", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({ id: "asset-video", projectId: "project-1", type: "video", durationMs: 5000 }),
        asset({ id: "asset-image", projectId: "project-1", type: "image", durationMs: null })
      ],
      timeline: timeline([])
    });

    expect(sourceTypeLabel("asset")).toBe("资产中心");
    expect(sourceTypeLabel("storyboard")).toBe("分镜规划");
    expect(sourceTypeLabel("voice_track")).toBe("配音中心");
    expect(cards.map((card) => card.durationLabel)).toEqual(["00:05", "无时长"]);
  });

  it("输出项目标识和包含类型及时长的摘要", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [asset({ id: "asset-summary", projectId: "project-1", type: "video", durationMs: 5000 })],
      timeline: timeline([])
    });

    expect(cards[0]).toMatchObject({
      projectId: "project-1"
    });
    expect(cards[0].summary).toContain("视频");
    expect(cards[0].summary).toContain("00:05");
  });

  it("缩略图路径缺失时回退到 thumbnailStatus.path", () => {
    const cards = buildWorkspaceAssetCards({
      projectId: "project-1",
      assets: [
        asset({
          id: "asset-thumbnail-fallback",
          projectId: "project-1",
          thumbnailPath: null,
          thumbnailStatusPath: "D:/tkops/thumbs/fallback.jpg"
        })
      ],
      timeline: timeline([])
    });

    expect(cards[0].thumbnailPath).toBe("D:/tkops/thumbs/fallback.jpg");
    expect(cards[0].previewAsset.thumbnailPath).toBe("D:/tkops/thumbs/fallback.jpg");
  });

  it("无资产且存在三类来源时默认选择优先级最高的分镜来源", () => {
    const defaultTab = resolveDefaultWorkspaceAssetTab({
      projectId: "project-1",
      assets: [],
      timeline: timeline([
        timelineClip({ id: "clip-voice", sourceType: "voice_track", trackId: "track-audio" }),
        timelineClip({ id: "clip-subtitle", sourceType: "subtitle_track", trackId: "track-subtitle" }),
        timelineClip({ id: "clip-storyboard", sourceType: "storyboard", trackId: "track-video" })
      ])
    });

    expect(defaultTab).toBe("storyboard");
  });

  it("无资产且无来源片段时默认保持资产空态", () => {
    const defaultTab = resolveDefaultWorkspaceAssetTab({
      projectId: "project-1",
      assets: [],
      timeline: timeline([
        timelineClip({ id: "clip-manual", sourceType: "manual", trackId: "track-video" })
      ])
    });

    expect(defaultTab).toBe("assets");
  });

  it("存在当前项目资产时默认保持资产 tab", () => {
    const defaultTab = resolveDefaultWorkspaceAssetTab({
      projectId: "project-1",
      assets: [asset({ id: "asset-video", projectId: "project-1" })],
      timeline: timeline([
        timelineClip({ id: "clip-storyboard", sourceType: "storyboard", trackId: "track-video" })
      ])
    });

    expect(defaultTab).toBe("assets");
  });

  it("把时间线片段来源映射为素材池来源 tab", () => {
    expect(resolveWorkspaceAssetTabFromSourceType("storyboard")).toBe("storyboard");
    expect(resolveWorkspaceAssetTabFromSourceType("voice_track")).toBe("voice_track");
    expect(resolveWorkspaceAssetTabFromSourceType("subtitle_track")).toBe("subtitle_track");
    expect(resolveWorkspaceAssetTabFromSourceType("asset")).toBeNull();
  });
});

function asset(input: {
  id: string;
  projectId: string | null;
  sourceProjectId?: string | null;
  type?: string;
  durationMs?: number | null;
  availabilityStatus?: string;
  nextAction?: string | null;
  thumbnailPath?: string | null;
  thumbnailStatusPath?: string | null;
}): AssetDto {
  return {
    id: input.id,
    name: input.id,
    type: input.type ?? "video",
    source: "asset",
    filePath: `D:/tkops/${input.id}.mp4`,
    fileSizeBytes: 1024,
    durationMs: "durationMs" in input ? input.durationMs ?? null : 5000,
    thumbnailPath: "thumbnailPath" in input ? input.thumbnailPath ?? null : null,
    tags: null,
    projectId: input.projectId,
    metadataJson: null,
    sourceInfo: {
      source: "import",
      projectId: input.sourceProjectId ?? null,
      groupId: null,
      filePath: null,
      metadataSummary: {}
    },
    availability: {
      status: input.availabilityStatus ?? "available",
      errorCode: null,
      errorMessage: null,
      nextAction: input.nextAction ?? null
    },
    referenceSummary: {
      total: 0,
      referenceTypes: [],
      blockingDelete: false
    },
    thumbnailStatus: {
      status: "ready",
      path: input.thumbnailStatusPath ?? null,
      generatedAt: null
    },
    createdAt: "2026-05-15T00:00:00.000Z",
    updatedAt: "2026-05-15T00:00:00.000Z"
  };
}

function timeline(clips: WorkspaceTimelineDto["tracks"][number]["clips"]): WorkspaceTimelineDto {
  return {
    id: "timeline-1",
    projectId: "project-1",
    name: "主时间线",
    status: "draft",
    durationSeconds: 5,
    source: "manual",
    tracks: [
      {
        id: "track-video",
        kind: "video",
        name: "视频轨",
        orderIndex: 0,
        locked: false,
        muted: false,
        clips
      }
    ],
    createdAt: "2026-05-15T00:00:00.000Z",
    updatedAt: "2026-05-15T00:00:00.000Z"
  };
}

function timelineClip(input: {
  id: string;
  sourceType: string;
  trackId: string;
}): WorkspaceTimelineDto["tracks"][number]["clips"][number] {
  return {
    id: input.id,
    trackId: input.trackId,
    sourceType: input.sourceType,
    sourceId: input.id,
    label: input.id,
    startMs: 0,
    durationMs: 5000,
    inPointMs: 0,
    outPointMs: null,
    status: "ready"
  };
}
