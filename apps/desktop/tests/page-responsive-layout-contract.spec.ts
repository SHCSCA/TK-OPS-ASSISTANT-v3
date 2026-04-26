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
    expect(css).toMatch(/\.editor-mode-switch\s*{[\s\S]*display:\s*inline-flex;/);
    expect(css).toMatch(/\.editor-mode-switch__button\s*{[\s\S]*min-width:\s*56px;/);
    expect(css).toMatch(/\.editor-mode-switch__button\.is-active\s*{[\s\S]*box-shadow:\s*var\(--shadow-xs\);/);
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

  it("keeps AI editing workspace panels from overlapping when detail panel narrows content", () => {
    const css = readSource("../src/pages/workspace/AIEditingWorkspacePage.css");

    expect(css).toMatch(/\.page-container\s*{[\s\S]*width:\s*100%;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(css).toMatch(/\.page-container\s*{[\s\S]*container-name:\s*editing-workspace;/);
    expect(css).not.toContain("height: 400px");
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(min\(100%,\s*240px\),\s*280px\)\s+minmax\(0,\s*1fr\)\s+minmax\(min\(100%,\s*240px\),\s*280px\);/);
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*flex:\s*1\s+1\s+auto;/);
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*min-height:\s*0;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*260px\)\s+minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
  });
});
