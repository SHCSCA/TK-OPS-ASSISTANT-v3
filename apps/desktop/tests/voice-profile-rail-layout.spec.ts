import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("配音音色栏布局契约", () => {
  it("音色列表必须拥有独立纵向滚动视口", () => {
    const source = readSource("../src/modules/voice/VoiceProfileRail.vue");
    const panelShell = source.match(/\.panel-shell\s*{(?<body>[\s\S]*?)}/)?.groups?.body ?? "";
    const listViewport = source.match(/\.list-viewport\s*{(?<body>[\s\S]*?)}/)?.groups?.body ?? "";

    expect(panelShell).toContain("display: flex;");
    expect(panelShell).toContain("flex-direction: column;");
    expect(listViewport).toContain("overflow-y: auto;");
    expect(listViewport).toContain("overscroll-behavior: contain;");
    expect(listViewport).toContain("touch-action: pan-y;");
  });
});
