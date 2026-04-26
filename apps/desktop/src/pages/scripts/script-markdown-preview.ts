import MarkdownIt from "markdown-it";

const markdownRenderer = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: true,
  typographer: true
});

export function renderScriptMarkdownPreview(markdown: string): string {
  return markdownRenderer.render(normalizeScriptMarkdown(markdown));
}

export function normalizeScriptMarkdown(value: string): string {
  const normalized = value.replace(/\r\n/g, "\n").trim();
  if (normalized === "") {
    return "";
  }

  const lines = normalized.split("\n");
  if (lines.length >= 2 && isMarkdownFence(lines[0].trim()) && isMarkdownFence(lines[lines.length - 1].trim())) {
    return lines.slice(1, -1).join("\n").trim();
  }
  return normalized;
}

function isMarkdownFence(line: string): boolean {
  return /^(```|~~~)[a-z0-9_-]*$/i.test(line.trim());
}
