import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("page responsive layout contract", () => {
  it("keeps script workspace from overflowing compact desktop content", () => {
    const css = readSource("../src/pages/scripts/ScriptTopicCenterPage.css");

    expect(css).toMatch(/\.page-container\s*{[\s\S]*width:\s*100%;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(css).toMatch(/\.script-workspace\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.script-panel\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.script-card\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.editor-body\s*{[^}]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@media\s*\(max-width:\s*1200px\)\s*{[\s\S]*\.script-workspace\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
  });

  it("keeps storyboard view controls readable when the shell content narrows", () => {
    const css = readSource("../src/pages/storyboards/StoryboardPlanningCenterPage.css");

    expect(css).toMatch(/\.page-header__actions\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.view-switch\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.view-btn\s*{[\s\S]*min-width:\s*88px;/);
    expect(css).toMatch(/\.view-btn\s*{[\s\S]*white-space:\s*nowrap;/);
  });

  it("keeps review workspace content inside the shell content host", () => {
    const css = readSource("../src/pages/review/review-optimization-center.css");

    expect(css).toMatch(/\.page-container\s*{[\s\S]*width:\s*100%;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(css).toMatch(/\.workspace-grid\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.workspace-main\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.workspace-rail\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.kpi-grid\s*{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(min\(100%,\s*140px\),\s*1fr\)\);/);
  });
});
