import type { ScriptSegmentDraft } from "./script-segment-types";

type MutableScriptSegment = {
  headingLevel: number | null;
  lines: string[];
  titleLine: string | null;
};

const FALLBACK_BODY = "等待补充正文。";

export function parseScriptSegments(value: string): ScriptSegmentDraft[] {
  const normalized = normalizeScriptContent(value);
  if (normalized === "") {
    return [];
  }

  const segments: ScriptSegmentDraft[] = [];
  let current: MutableScriptSegment | null = null;

  const flushCurrent = () => {
    if (current === null) {
      return;
    }
    const draft = toScriptSegmentDraft(current, segments.length);
    if (draft !== null) {
      segments.push(draft);
    }
    current = null;
  };

  for (const line of normalized.split("\n")) {
    if (isMarkdownFence(line)) {
      continue;
    }

    if (isMarkdownSeparator(line)) {
      continue;
    }

    const heading = parseHeading(line);
    if (heading !== null) {
      flushCurrent();
      current = {
        headingLevel: heading.level,
        lines: [],
        titleLine: heading.title
      };
      continue;
    }

    if (current === null) {
      current = {
        headingLevel: null,
        lines: [],
        titleLine: null
      };
    }

    if (line.trim() === "") {
      if (current.lines.length > 0 && current.lines[current.lines.length - 1] !== "") {
        current.lines.push("");
      }
      continue;
    }

    current.lines.push(line.trimEnd());
  }

  flushCurrent();
  return segments;
}

export function updateScriptSegment(
  value: string,
  segmentId: string,
  patch: Partial<Pick<ScriptSegmentDraft, "title" | "body">>
): string {
  const segments = parseScriptSegments(value);
  const nextSegments = segments.map((segment) =>
    segment.id === segmentId
      ? {
          ...segment,
          title: patch.title ?? segment.title,
          body: patch.body ?? segment.body
        }
      : segment
  );
  return serializeScriptSegments(nextSegments);
}

export function serializeScriptSegments(segments: ScriptSegmentDraft[]): string {
  return segments
    .map((segment) => {
      const lines: string[] = [];
      if (segment.headingLevel !== null) {
        lines.push(`${"#".repeat(segment.headingLevel)} ${segment.title.trim()}`);
        if (segment.body.trim()) {
          lines.push("");
          lines.push(segment.body.trim());
        }
        return lines.join("\n");
      }

      lines.push(segment.title.trim());
      if (segment.body.trim()) {
        lines.push(segment.body.trim());
      }
      return lines.join("\n");
    })
    .filter((segment) => segment.trim().length > 0)
    .join("\n\n");
}

function toScriptSegmentDraft(
  current: MutableScriptSegment,
  index: number
): ScriptSegmentDraft | null {
  const lines = trimEmptyEdges(current.lines);
  if (current.headingLevel !== null) {
    const title = sanitizeInlineMarkdown(current.titleLine ?? "") || `段落 ${index + 1}`;
    const body = lines.join("\n").trim();
    return {
      id: `segment-${index + 1}`,
      title,
      body,
      excerpt: buildExcerpt(body),
      headingLevel: current.headingLevel,
      kind: "heading"
    };
  }

  if (lines.length === 0) {
    return null;
  }

  const [firstLine, ...restLines] = lines;
  const title = sanitizeInlineMarkdown(firstLine) || `段落 ${index + 1}`;
  const body = restLines.join("\n").trim();
  return {
    id: `segment-${index + 1}`,
    title,
    body,
    excerpt: buildExcerpt(body),
    headingLevel: null,
    kind: "lead"
  };
}

function buildExcerpt(body: string): string {
  const sanitized = sanitizeInlineMarkdown(
    body
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .join(" ")
  );
  return sanitized.slice(0, 88) || FALLBACK_BODY;
}

function normalizeScriptContent(value: string): string {
  return value.replace(/\r\n/g, "\n").trim();
}

function parseHeading(line: string): { level: number; title: string } | null {
  const matched = line.trim().match(/^(#{1,6})\s+(.+)$/);
  if (matched === null) {
    return null;
  }
  return {
    level: matched[1].length,
    title: matched[2].trim()
  };
}

function isMarkdownSeparator(line: string): boolean {
  const normalized = line.trim();
  return /^([-*_])\1{2,}$/.test(normalized);
}

function isMarkdownFence(line: string): boolean {
  return /^(```|~~~)[a-z0-9_-]*$/i.test(line.trim());
}

function trimEmptyEdges(lines: string[]): string[] {
  let start = 0;
  let end = lines.length;
  while (start < end && lines[start].trim() === "") {
    start += 1;
  }
  while (end > start && lines[end - 1].trim() === "") {
    end -= 1;
  }
  return lines.slice(start, end);
}

function sanitizeInlineMarkdown(value: string): string {
  return value
    .replace(/\|/g, " ")
    .replace(/[*_`>#-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
