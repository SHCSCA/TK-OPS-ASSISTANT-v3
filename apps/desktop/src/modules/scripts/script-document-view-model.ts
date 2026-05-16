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

export type ScriptSubtitleTableRow = {
  goal: string;
  segmentId: string;
  source: string;
  subtitle: string;
  time: string;
  voiceover: string;
};

export type ScriptWorkspaceTableRow = {
  goal: string;
  segmentId: string;
  source: string;
  subtitle: string;
  time: string;
  voiceover: string;
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

const LEGACY_SEGMENT_PREFIX_RE =
  /^(S\d{2,})\s+(\d+(?:\.\d+)?\s*[-–—]\s*\d+(?:\.\d+)?\s*(?:s|秒)?)\s+(.+)$/i;

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

export function extractScriptDocumentSubtitleRows(
  documentJson: ScriptDocumentJson | null | undefined,
  legacyContent = ""
): ScriptSubtitleTableRow[] {
  const document = isRecord(documentJson) ? documentJson : null;
  const segments = normalizeSegments(document?.segments);
  if (segments.length > 0) {
    return segments
      .map((segment, index) => ({
        goal: asText(segment.goal),
        segmentId: asText(segment.segmentId) || `S${String(index + 1).padStart(2, "0")}`,
        source: "结构化脚本",
        subtitle: asText(segment.subtitle) || asText(segment.voiceover),
        time: asText(segment.time),
        voiceover: asText(segment.voiceover)
      }))
      .filter((row) => row.subtitle || row.voiceover);
  }

  const legacySegmentRows = extractLegacySegmentRows(legacyContent);
  if (legacySegmentRows.length > 0) {
    return legacySegmentRows;
  }

  const directSubtitles = normalizeStringList(document?.subtitles || document?.subtitleFull);
  const fallbackLines =
    directSubtitles.length > 0
      ? directSubtitles.map((text) => ({ text, source: "字幕完整稿" }))
      : extractScriptDownstreamText(legacyContent, "subtitle").map((line) => ({
          text: line.text,
          source: "旧脚本"
        }));

  return fallbackLines.map((line, index) => ({
    goal: "",
    segmentId: `S${String(index + 1).padStart(2, "0")}`,
    source: line.source,
    subtitle: line.text,
    time: "",
    voiceover: ""
  }));
}

export function buildScriptWorkspaceTableRows(
  documentJson: ScriptDocumentJson | null | undefined,
  legacyContent = ""
): ScriptWorkspaceTableRow[] {
  const document = isRecord(documentJson) ? documentJson : null;
  const segments = normalizeSegments(document?.segments);
  if (segments.length > 0) {
    return segments
      .map((segment, index) => ({
        goal: asText(segment.goal),
        segmentId: asText(segment.segmentId) || `S${String(index + 1).padStart(2, "0")}`,
        source: "结构化脚本",
        subtitle: asText(segment.subtitle),
        time: asText(segment.time),
        voiceover: asText(segment.voiceover)
      }))
      .filter((row) => row.goal || row.subtitle || row.voiceover);
  }

  const legacyRows = extractLegacySegmentRows(legacyContent);
  if (legacyRows.length > 0) {
    return legacyRows.map((row) => ({
      goal: row.goal,
      segmentId: row.segmentId,
      source: row.source,
      subtitle: row.subtitle,
      time: row.time,
      voiceover: row.voiceover || row.subtitle
    }));
  }

  const markdownRows = extractMarkdownWorkspaceRows(legacyContent);
  if (markdownRows.length > 0) {
    return markdownRows;
  }

  const fallbackLines = extractScriptDownstreamText(legacyContent, "voice").map((line) => line.text);
  const plainLines = fallbackLines.length > 0 ? fallbackLines : extractWorkspacePlainLines(legacyContent);
  return plainLines.map((text, index) => ({
    goal: "",
    segmentId: `S${String(index + 1).padStart(2, "0")}`,
    source: "旧脚本",
    subtitle: text,
    time: "",
    voiceover: text
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

function extractLegacySegmentRows(content: string): ScriptSubtitleTableRow[] {
  return content
    .split(/\r?\n+/)
    .map(cleanText)
    .map((line) => {
      const match = line.match(LEGACY_SEGMENT_PREFIX_RE);
      if (!match) {
        return null;
      }
      return {
        goal: "",
        segmentId: match[1].toUpperCase(),
        source: "旧脚本段落",
        subtitle: cleanText(match[3]),
        time: normalizeLegacyTime(match[2]),
        voiceover: ""
      };
    })
    .filter((row): row is ScriptSubtitleTableRow => Boolean(row));
}

function extractMarkdownWorkspaceRows(content: string): ScriptWorkspaceTableRow[] {
  const rows: ScriptWorkspaceTableRow[] = [];
  for (const block of collectMarkdownTableBlocks(content)) {
    const parsedRows = block.map(parseMarkdownTableRow).filter((row) => row.length > 0);
    if (parsedRows.length < 3 || !isMarkdownTableSeparator(parsedRows[1])) {
      continue;
    }

    const headers = parsedRows[0].map(cleanText);
    const idIndex = findHeaderIndex(headers, [/^段落\s*ID$/i, /^段落$/i, /^序号$/i, /^镜头$/i]);
    const timeIndex = findHeaderIndex(headers, [/时间/, /时长/]);
    const goalIndex = findHeaderIndex(headers, [/段落目标/, /目标/, /留存点/]);
    const voiceIndex = findHeaderIndex(headers, [/口播文案/, /口播/, /台词/, /对白/, /旁白/]);
    const subtitleIndex = findHeaderIndex(headers, [/屏幕字幕/, /^字幕$/]);
    const visualIndex = findHeaderIndex(headers, [/画面内容/, /画面描述/, /基础画面/, /^画面$/, /^内容$/]);

    for (const cells of parsedRows.slice(2)) {
      const visual = cleanText(cells[visualIndex] ?? "");
      const spoken = cleanText(cells[voiceIndex] ?? cells[subtitleIndex] ?? "");
      const voiceover = joinUniqueText([visual, spoken]);
      const subtitle = cleanText(cells[subtitleIndex] ?? voiceover);
      const goal = cleanText(cells[goalIndex] ?? "");
      if (!voiceover && !subtitle && !goal) {
        continue;
      }
      rows.push({
        goal,
        segmentId: normalizeWorkspaceSegmentId(cells[idIndex] ?? "", rows.length),
        source: "Markdown 表格",
        subtitle,
        time: cleanText(cells[timeIndex] ?? ""),
        voiceover
      });
    }
  }
  return rows;
}

function extractWorkspacePlainLines(content: string): string[] {
  return content
    .split(/\r?\n+/)
    .map(cleanWorkspaceLine)
    .filter(Boolean);
}

function cleanWorkspaceLine(value: string): string {
  const normalized = value.trim();
  if (!normalized || /^(```|~~~)/.test(normalized) || /^[-*_]{3,}$/.test(normalized) || isMarkdownTableLine(normalized)) {
    return "";
  }
  return normalized
    .replace(/^#{1,6}\s+/, "")
    .replace(/^[-*+]\s+/, "")
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function joinUniqueText(items: string[]): string {
  const result: string[] = [];
  for (const item of items.map(cleanText).filter(Boolean)) {
    if (!result.some((value) => normalizeCompareText(value) === normalizeCompareText(item))) {
      result.push(item);
    }
  }
  return result.join(" / ");
}

function normalizeCompareText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function collectMarkdownTableBlocks(content: string): string[][] {
  const blocks: string[][] = [];
  let current: string[] = [];
  for (const line of content.split(/\r?\n/)) {
    if (isMarkdownTableLine(line)) {
      current.push(line.trim());
      continue;
    }
    if (current.length > 0) {
      blocks.push(current);
      current = [];
    }
  }
  if (current.length > 0) {
    blocks.push(current);
  }
  return blocks;
}

function parseMarkdownTableRow(line: string): string[] {
  const trimmed = line.trim();
  if (!isMarkdownTableLine(trimmed)) {
    return [];
  }
  return trimmed
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isMarkdownTableLine(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|");
}

function isMarkdownTableSeparator(row: string[]): boolean {
  return row.length > 0 && row.every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function findHeaderIndex(headers: string[], patterns: RegExp[]): number {
  return headers.findIndex((header) => patterns.some((pattern) => pattern.test(header)));
}

function normalizeWorkspaceSegmentId(value: string, index: number): string {
  const text = cleanText(value);
  if (/^S\d{1,}$/i.test(text)) {
    return text.toUpperCase();
  }
  if (/^\d+$/.test(text)) {
    return `S${text.padStart(2, "0")}`;
  }
  return text || `S${String(index + 1).padStart(2, "0")}`;
}

function normalizeLegacyTime(value: string): string {
  return value.replace(/\s+/g, "");
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
