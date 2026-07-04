import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

describe("M05 页面体量契约", () => {
  it("AI 剪辑工作台页面不超过 600 行", () => {
    const testDir = dirname(fileURLToPath(import.meta.url));
    const pagePath = resolve(testDir, "../src/pages/workspace/AIEditingWorkspacePage.vue");
    const lineCount = readFileSync(pagePath, "utf-8").split(/\r?\n/).length;

    expect(lineCount).toBeLessThanOrEqual(600);
  });
});
