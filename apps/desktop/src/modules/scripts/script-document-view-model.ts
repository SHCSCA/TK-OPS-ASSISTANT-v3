import { estimateScriptLineDuration, extractScriptDownstreamText } from "@/modules/scripts/script-downstream-text";

export type ScriptDocumentJson = Record<string, any>;

export type ScriptDocumentTable = {
  headers: string[];
  rows: string[][];
};

export type ScriptDocumentSection = {
  title: string;
  kind: "text" | "list" | "table";
  text?: string;
  items?: string[];
  table?: ScriptDocumentTable;
};

export type ScriptDocumentViewModel = {
  title: string;
  infoTable: ScriptDocumentTable;
  segmentTable: ScriptDocumentTable;
  sections: ScriptDocumentSection[];
};

export type ScriptDownstreamPurpose = "voice" | "subtitle";

export type ScriptDownstreamLine = {
  text: string;
  estimatedDuration: number;
};

const SEGMENT_HEADERS = [
  "段落ID",
  "时间",
  "段落目标",
  "口播文案",
  "屏幕字幕",
  "基础画面建议",
  "留存点",
  "给分镜Agent的提示"
];

export function buildScriptDocumentViewModel(documentJson: ScriptDocumentJson | null | undefined): ScriptDocumentViewModel {
  const document = isRecord(documentJson) ? documentJson : {};
  const metadata = isRecord(document.metadata) ? document.metadata : {};
  const segments = normalizeSegments(document.segments);

  return {
    title: asText(document.title) || "TikTok 短视频脚本",
    infoTable: {
      headers: ["项目", "内容"],
      rows: buildInfoRows(metadata)
    },
    segmentTable: {
      headers: SEGMENT_HEADERS,
      rows: segments.map((segment, index) => [
        asText(segment.segmentId) || `S${String(index + 1).padStart(2, "0")}`,
        asText(segment.time),
        asText(segment.goal),
        asText(segment.voiceover),
        asText(segment.subtitle),
        asText(segment.visualSuggestion),
        asText(segment.retentionPoint),
        asText(segment.storyboardHint)
      ])
    },
    sections: buildSections(document)
  };
}

export function extractScriptDocumentDownstreamText(
  documentJson: ScriptDocumentJson | null | undefined,
  purpose: ScriptDownstreamPurpose,
  legacyContent = ""
): ScriptDownstreamLine[] {
  const document = isRecord(documentJson) ? documentJson : null;
  if (!document) {
    return extractScriptDownstreamText(legacyContent, purpose);
  }

  const directLines =
    purpose === "voice"
      ? splitText(asText(document.voiceoverFull || document.fullVoiceover))
      : normalizeStringList(document.subtitles || document.subtitleFull);
  const lines = directLines.length > 0 ? directLines : normalizeSegments(document.segments).map((segment) =>
    asText(purpose === "voice" ? segment.voiceover : segment.subtitle)
  );

  const useful = lines.map(cleanText).filter(Boolean);
  if (useful.length === 0) {
    return extractScriptDownstreamText(legacyContent, purpose);
  }
  return useful.map((text) => ({
    text,
    estimatedDuration: estimateScriptLineDuration(text)
  }));
}

export function buildScriptPlainText(documentJson: ScriptDocumentJson | null | undefined, legacyContent = ""): string {
  const document = isRecord(documentJson) ? documentJson : null;
  if (!document) {
    return legacyContent;
  }
  const view = buildScriptDocumentViewModel(document);
  const lines = [view.title, ...view.segmentTable.rows.map((row) => `${row[0]} ${row[3]}`.trim())];
  return lines.filter(Boolean).join("\n");
}

function buildInfoRows(metadata: Record<string, any>): string[][] {
  const entries: Array<[string, string]> = [
    ["平台", "platform"],
    ["视频比例", "videoRatio"],
    ["建议时长", "duration"],
    ["目标用户", "targetUsers"],
    ["视频目的", "videoGoal"],
    ["内容风格", "contentStyle"],
    ["拍摄方式", "shootingMethod"],
    ["语言", "language"],
    ["脚本版本", "scriptVersion"],
    ["下游建议", "handoff"]
  ];
  return entries
    .map(([label, key]) => [label, asText(metadata[key])])
    .filter((row) => row[1]);
}

function buildSections(document: Record<string, any>): ScriptDocumentSection[] {
  const sections: ScriptDocumentSection[] = [];
  const strategy = isRecord(document.strategy) ? document.strategy : null;
  if (strategy) {
    sections.push({
      title: "视频核心策略",
      kind: "table",
      table: {
        headers: ["项目", "内容"],
        rows: Object.entries(strategy).map(([key, value]) => [strategyLabel(key), asText(value)])
      }
    });
  }

  const hooks = normalizeStringList(document.hooks);
  if (hooks.length > 0) {
    sections.push({ title: "爆款开头钩子", kind: "list", items: hooks });
  }

  const voiceover = splitText(asText(document.voiceoverFull || document.fullVoiceover));
  if (voiceover.length > 0) {
    sections.push({ title: "口播完整稿", kind: "list", items: voiceover });
  }

  const subtitles = normalizeStringList(document.subtitles || document.subtitleFull);
  if (subtitles.length > 0) {
    sections.push({ title: "字幕完整稿", kind: "list", items: subtitles });
  }

  const cta = isRecord(document.cta) ? document.cta : null;
  if (cta) {
    sections.push({
      title: "结尾 CTA",
      kind: "table",
      table: {
        headers: ["类型", "文案"],
        rows: Object.entries(cta).map(([key, value]) => [ctaLabel(key), asText(value)])
      }
    });
  }
  return sections;
}

function normalizeSegments(value: unknown): Array<Record<string, any>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => (isRecord(item) ? asText(item.text || item.value) : asText(item))).filter(Boolean);
  }
  return splitText(asText(value));
}

function splitText(value: string): string[] {
  return value.split(/\r?\n+/).map(cleanText).filter(Boolean);
}

function cleanText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
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

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function strategyLabel(key: string): string {
  const labels: Record<string, string> = {
    complianceNote: "合规处理",
    contentAngle: "内容切入角度",
    conversionGoal: "转化目标",
    corePainPoint: "核心痛点",
    mainHook: "主要看点",
    userEmotion: "用户情绪"
  };
  return labels[key] ?? key;
}

function ctaLabel(key: string): string {
  const labels: Record<string, string> = {
    comment: "评论引导",
    conversion: "转化引导",
    save: "收藏引导"
  };
  return labels[key] ?? key;
}
