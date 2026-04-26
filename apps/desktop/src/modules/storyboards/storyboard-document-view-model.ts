import type { StoryboardScene } from "@/types/runtime";

export type StoryboardDocumentJson = Record<string, any>;

export type StoryboardDocumentTable = {
  headers: string[];
  rows: string[][];
};

export type StoryboardShotView = {
  shotId: string;
  segmentId: string;
  time: string;
  shotSize: string;
  visualContent: string;
  action: string;
  cameraAngle: string;
  cameraMovement: string;
  voiceover: string;
  subtitle: string;
  audio: string;
  shootingNote: string;
  visualPrompt: string;
  transition: string;
};

export type StoryboardViewModel = {
  title: string;
  infoTable: StoryboardDocumentTable;
  shotTable: StoryboardDocumentTable;
  shots: StoryboardShotView[];
};

const SHOT_HEADERS = [
  "镜头",
  "段落",
  "时间",
  "景别",
  "画面内容",
  "人物动作",
  "镜头角度",
  "运镜方式",
  "口播文案",
  "屏幕字幕",
  "音效/BGM",
  "拍摄注意"
];

export function buildStoryboardViewModel(storyboardJson: StoryboardDocumentJson | null | undefined): StoryboardViewModel {
  const document = isRecord(storyboardJson) ? storyboardJson : {};
  const metadata = isRecord(document.metadata) ? document.metadata : {};
  const shots = normalizeShots(document.shots);
  const shotViews = shots.map((shot, index) => buildShotView(shot, index));
  return {
    title: "TikTok 分镜规划文档",
    infoTable: {
      headers: ["项目", "内容"],
      rows: [
        ["分镜ID", asText(metadata.storyboardId)],
        ["脚本版本", asText(metadata.basedOnScriptRevision)],
        ["视频比例", asText(metadata.videoRatio)],
        ["目标时长", asText(metadata.targetDurationSec)],
        ["镜头数量", asText(metadata.shotCount || shots.length)]
      ].filter((row) => row[1])
    },
    shotTable: {
      headers: SHOT_HEADERS,
      rows: shotViews.map((shot) => [
        shot.shotId,
        shot.segmentId,
        shot.time,
        shot.shotSize,
        shot.visualContent,
        shot.action,
        shot.cameraAngle,
        shot.cameraMovement,
        shot.voiceover,
        shot.subtitle,
        shot.audio,
        shot.shootingNote
      ])
    },
    shots: shotViews
  };
}

export function buildStoryboardScenesFromJson(storyboardJson: StoryboardDocumentJson | null | undefined): StoryboardScene[] {
  const document = isRecord(storyboardJson) ? storyboardJson : {};
  return normalizeShots(document.shots).map((shot, index) => {
    const shotView = buildShotView(shot, index);
    const visualPrompt = shotView.visualPrompt || shotView.visualContent;
    return {
      sceneId: shotView.shotId,
      title: asText(shot.title) || [shotView.shotId, shotView.segmentId].filter(Boolean).join(" · "),
      summary: shotView.visualContent || visualPrompt || shotView.shotId,
      visualPrompt: visualPrompt || shotView.visualContent || shotView.shotId,
      action: shotView.action,
      audio: shotView.audio,
      cameraAngle: shotView.cameraAngle,
      cameraMovement: shotView.cameraMovement,
      shootingNote: shotView.shootingNote,
      shotLabel: shotView.segmentId,
      shotSize: shotView.shotSize,
      subtitle: shotView.subtitle,
      time: shotView.time,
      transition: shotView.transition,
      visualContent: shotView.visualContent,
      voiceover: shotView.voiceover
    };
  });
}

function buildShotView(shot: Record<string, any>, index: number): StoryboardShotView {
  return {
    shotId: asText(shot.shotId) || `SH${String(index + 1).padStart(2, "0")}`,
    segmentId: asText(shot.segmentId),
    time: asText(shot.time),
    shotSize: asText(shot.shotSize),
    visualContent: asText(shot.visualContent || shot.summary),
    action: asText(shot.action),
    cameraAngle: asText(shot.cameraAngle),
    cameraMovement: asText(shot.cameraMovement),
    voiceover: normalizeRepeatedText(shot.voiceover),
    subtitle: normalizeRepeatedText(shot.subtitle),
    audio: asText(shot.audio),
    shootingNote: asText(shot.shootingNote),
    visualPrompt: asText(shot.visualPrompt),
    transition: asText(shot.transition)
  };
}

function normalizeShots(value: unknown): Array<Record<string, any>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function asText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value).trim();
  }
  return "";
}

function normalizeRepeatedText(value: unknown): string {
  const text = asText(value);
  if (!text.includes("/")) {
    return text;
  }
  const parts = text
    .split("/")
    .map((item) => item.trim())
    .filter(Boolean);
  const uniqueParts = parts.filter((part, index) => parts.findIndex((item) => item === part) === index);
  return uniqueParts.length > 0 ? uniqueParts.join(" / ") : text;
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
