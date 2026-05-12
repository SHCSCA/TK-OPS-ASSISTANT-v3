export function renderScriptMarkdownPreview(markdown: string): string {
  const normalized = normalizeScriptMarkdown(markdown);
  if (normalized === "") {
    return "";
  }

  return renderBlocks(normalized.split("\n"));
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

function renderBlocks(lines: string[]): string {
  const html: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index]?.trim() ?? "";
    if (!line) {
      index += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      html.push(`<h${level}>${escapeHtml(heading[2].trim())}</h${level}>`);
      index += 1;
      continue;
    }

    if (isTableStart(lines, index)) {
      const rendered = renderTable(lines, index);
      html.push(rendered.html);
      index = rendered.nextIndex;
      continue;
    }

    if (/^[-*_]{3,}$/.test(line)) {
      html.push("<hr>");
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const rendered = renderList(lines, index);
      html.push(rendered.html);
      index = rendered.nextIndex;
      continue;
    }

    const rendered = renderParagraph(lines, index);
    html.push(rendered.html);
    index = rendered.nextIndex;
  }

  return html.join("");
}

function renderTable(lines: string[], startIndex: number): { html: string; nextIndex: number } {
  const header = splitTableRow(lines[startIndex]);
  const rows: string[][] = [];
  let index = startIndex + 2;

  while (index < lines.length) {
    const cells = splitTableRow(lines[index] ?? "");
    if (!cells.length) {
      break;
    }
    rows.push(cells);
    index += 1;
  }

  const thead = `<thead><tr>${header.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  return {
    html: `<table>${thead}${tbody}</table>`,
    nextIndex: index
  };
}

function renderList(lines: string[], startIndex: number): { html: string; nextIndex: number } {
  const items: string[] = [];
  let index = startIndex;

  while (index < lines.length) {
    const line = lines[index]?.trim() ?? "";
    if (!/^[-*]\s+/.test(line)) {
      break;
    }
    items.push(line.replace(/^[-*]\s+/, "").trim());
    index += 1;
  }

  return {
    html: `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`,
    nextIndex: index
  };
}

function renderParagraph(lines: string[], startIndex: number): { html: string; nextIndex: number } {
  const content: string[] = [];
  let index = startIndex;

  while (index < lines.length) {
    const line = lines[index]?.trim() ?? "";
    if (!line || /^(#{1,6})\s+/.test(line) || isTableStart(lines, index) || /^[-*]\s+/.test(line)) {
      break;
    }
    content.push(line);
    index += 1;
  }

  return {
    html: `<p>${escapeHtml(content.join(" "))}</p>`,
    nextIndex: index
  };
}

function isTableStart(lines: string[], index: number): boolean {
  return splitTableRow(lines[index] ?? "").length > 0 && isTableSeparator(lines[index + 1] ?? "");
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) {
    return [];
  }
  return trimmed
    .slice(1, -1)
    .split("|")
    .map((cell) => cell.trim());
}

function isTableSeparator(line: string): boolean {
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function isMarkdownFence(line: string): boolean {
  return /^(```|~~~)[a-z0-9_-]*$/i.test(line.trim());
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
