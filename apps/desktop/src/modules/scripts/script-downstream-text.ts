export type ScriptDownstreamTextPurpose = "voice" | "subtitle";

export interface ScriptDownstreamTextLine {
  text: string;
  estimatedDuration: number;
}

const VOICE_TABLE_HEADERS = [/口播/, /台词/, /对白/, /旁白/];
const SUBTITLE_TABLE_HEADERS = [/屏幕字幕/, /字幕/];
const VOICE_SECTION_TITLES = [/口播完整稿/, /完整口播/];
const SUBTITLE_SECTION_TITLES = [/字幕完整稿/, /完整字幕/];

export function extractScriptDownstreamText(
  content: string,
  purpose: ScriptDownstreamTextPurpose
): ScriptDownstreamTextLine[] {
  const normalized = content.replace(/\r\n/g, "\n");
  const candidates =
    purpose === "subtitle"
      ? [
          extractSectionLines(normalized, SUBTITLE_SECTION_TITLES),
          extractTableColumnLines(normalized, SUBTITLE_TABLE_HEADERS),
          extractTableColumnLines(normalized, VOICE_TABLE_HEADERS)
        ]
      : [
          extractTableColumnLines(normalized, VOICE_TABLE_HEADERS),
          extractSectionLines(normalized, VOICE_SECTION_TITLES)
        ];

  const lines = candidates.find((items) => items.length > 0) ?? extractPlainLines(normalized);

  return lines.map((text) => ({
    text,
    estimatedDuration: estimateScriptLineDuration(text)
  }));
}

export function estimateScriptLineDuration(text: string): number {
  return Math.round(text.length * 0.4 * 10) / 10;
}

function extractSectionLines(content: string, titlePatterns: RegExp[]): string[] {
  const lines = content.split("\n");
  const result: string[] = [];
  let active = false;
  let inFence = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^#{1,6}\s+/.test(trimmed)) {
      if (active) {
        break;
      }
      active = titlePatterns.some((pattern) => pattern.test(cleanMarkdownText(trimmed)));
      continue;
    }

    if (!active) {
      continue;
    }

    if (/^```/.test(trimmed)) {
      inFence = !inFence;
      continue;
    }

    const cleaned = cleanMarkdownText(line);
    if (cleaned && (inFence || isUsefulLine(cleaned))) {
      result.push(cleaned);
    }
  }

  return result;
}

function extractTableColumnLines(content: string, headerPatterns: RegExp[]): string[] {
  const result: string[] = [];

  for (const block of collectTableBlocks(content)) {
    const rows = block.map(parseTableRow).filter((row) => row.length > 0);
    if (rows.length < 3) {
      continue;
    }

    const header = rows[0];
    const targetIndex = header.findIndex((cell) =>
      headerPatterns.some((pattern) => pattern.test(cleanMarkdownText(cell)))
    );
    if (targetIndex < 0) {
      continue;
    }

    for (const row of rows.slice(1)) {
      if (isSeparatorRow(row)) {
        continue;
      }
      const text = cleanMarkdownText(row[targetIndex] ?? "");
      if (isUsefulLine(text)) {
        result.push(text);
      }
    }
  }

  return result;
}

function collectTableBlocks(content: string): string[][] {
  const blocks: string[][] = [];
  let current: string[] = [];

  for (const line of content.split("\n")) {
    if (isTableLine(line)) {
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

function isTableLine(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|");
}

function parseTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isSeparatorRow(row: string[]): boolean {
  return row.every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function extractPlainLines(content: string): string[] {
  return content
    .split(/\n+/)
    .filter((line) => !/^\s*#{1,6}\s+/.test(line.trim()))
    .filter((line) => !isTableLine(line))
    .map(cleanMarkdownText)
    .filter(isUsefulLine);
}

function cleanMarkdownText(value: string): string {
  return collapseRepeatedSlashText(
    value
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/\\\|/g, "|")
      .replace(/^#{1,6}\s+/, "")
      .replace(/^[-*+]\s+/, "")
      .replace(/\*\*/g, "")
      .replace(/`/g, "")
      .replace(/^\s*(口播文案|屏幕字幕|字幕|台词|对白|旁白)\s*[:：]\s*/i, "")
      .replace(/^["“”]+|["“”]+$/g, "")
      .replace(/\s+/g, " ")
      .trim()
  );
}

function collapseRepeatedSlashText(text: string): string {
  const parts = text.split(/\s+\/\s+/).map((item) => item.trim());
  if (parts.length === 2 && normalizeForCompare(parts[0]) === normalizeForCompare(parts[1])) {
    return parts[0];
  }
  return text;
}

function normalizeForCompare(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function isUsefulLine(text: string): boolean {
  if (!text || /^[-—|/\\\s]+$/.test(text)) {
    return false;
  }
  if (/^```/.test(text) || isTableLine(text)) {
    return false;
  }
  return true;
}
