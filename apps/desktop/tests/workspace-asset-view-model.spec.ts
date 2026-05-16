import { describe, expect, it } from "vitest";

import {
  buildWorkspaceAssetCards,
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

  it("把已在时间线中的素材标记为已入轨并提供替换片段操作", () => {
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
      primaryAction: "替换片段"
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

  it("把缺失素材显示为路径缺失并使用重新定位操作", () => {
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
      primaryAction: "重新定位"
    });
  });

  it("缺失素材存在 nextAction 时优先使用 nextAction", () => {
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
      primaryAction: "选择新路径"
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
      primaryAction: "检查"
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
