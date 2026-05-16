import type { AssetDto, WorkspaceTimelineDto } from "@/types/runtime";

export type WorkspaceAssetTone = "neutral" | "success" | "warning" | "danger";

export type WorkspaceAssetCard = {
  id: string;
  projectId: string | null;
  name: string;
  type: string;
  filePath: string | null;
  thumbnailPath: string | null;
  durationLabel: string;
  summary: string;
  sourceTypeLabel: string;
  status: string;
  tone: WorkspaceAssetTone;
  primaryAction: string;
  isOnTimeline: boolean;
  asset: AssetDto;
};

export type BuildWorkspaceAssetCardsInput = {
  projectId: string;
  assets: AssetDto[];
  timeline: WorkspaceTimelineDto | null;
};

export function buildWorkspaceAssetCards(input: BuildWorkspaceAssetCardsInput): WorkspaceAssetCard[] {
  const timelineAssetIds = new Set(
    input.timeline?.tracks.flatMap((track) =>
      track.clips
        .filter((clip) => clip.sourceType === "asset" && clip.sourceId)
        .map((clip) => clip.sourceId as string)
    ) ?? []
  );

  return input.assets
    .filter((asset) => asset.projectId === input.projectId || asset.sourceInfo.projectId === input.projectId)
    .map((asset) => {
      const isOnTimeline = timelineAssetIds.has(asset.id);
      const state = resolveAssetState(asset, isOnTimeline);
      const durationLabel = formatDuration(asset.durationMs);

      return {
        id: asset.id,
        projectId: asset.projectId,
        name: asset.name,
        type: asset.type,
        filePath: asset.filePath,
        thumbnailPath: asset.thumbnailPath || asset.thumbnailStatus.path,
        durationLabel,
        summary: [assetTypeLabel(asset.type), durationLabel, formatFileSize(asset.fileSizeBytes)].join(" · "),
        sourceTypeLabel: sourceTypeLabel(asset.sourceInfo.source || asset.source),
        isOnTimeline,
        asset,
        ...state
      };
    });
}

export function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "storyboard") return "分镜规划";
  if (sourceType === "asset") return "资产中心";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音中心";
  if (sourceType === "subtitle_track") return "字幕对齐";
  if (sourceType === "manual") return "手动片段";
  if (sourceType === "import") return "本地导入";
  return sourceType;
}

function resolveAssetState(
  asset: AssetDto,
  isOnTimeline: boolean
): Pick<WorkspaceAssetCard, "status" | "tone" | "primaryAction"> {
  if (asset.availability.status === "missing") {
    return {
      status: "路径缺失",
      tone: "danger",
      primaryAction: asset.availability.nextAction || "重新定位"
    };
  }

  if (asset.availability.status === "needs_transcode") {
    return {
      status: "需转码",
      tone: "warning",
      primaryAction: "检查"
    };
  }

  if (isOnTimeline) {
    return {
      status: "已入轨",
      tone: "success",
      primaryAction: "替换片段"
    };
  }

  return {
    status: "可用",
    tone: "neutral",
    primaryAction: asset.type === "audio" ? "加入音轨" : "加入轨道"
  };
}

function formatDuration(durationMs: number | null): string {
  if (durationMs === null) return "无时长";

  const totalSeconds = Math.max(0, Math.floor(durationMs / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const parts = hours > 0 ? [hours, minutes, seconds] : [minutes, seconds];

  return parts.map((part) => String(part).padStart(2, "0")).join(":");
}

function assetTypeLabel(type: string): string {
  if (type === "video") return "视频";
  if (type === "audio") return "音频";
  if (type === "image") return "图片";
  return type;
}

function formatFileSize(fileSizeBytes: number | null): string {
  if (fileSizeBytes === null) return "未知大小";
  if (fileSizeBytes < 1024) return `${fileSizeBytes} B`;
  if (fileSizeBytes < 1024 * 1024) return `${(fileSizeBytes / 1024).toFixed(1)} KB`;
  if (fileSizeBytes < 1024 * 1024 * 1024) return `${(fileSizeBytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(fileSizeBytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
}
