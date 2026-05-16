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

  it("keeps storyboard list workspace readable when the shell content narrows", () => {
    const css = readSource("../src/pages/storyboards/StoryboardPlanningCenterPage.css");
    const table = readSource("../src/pages/storyboards/components/StructuredTable.vue");

    expect(css).toMatch(/\.page-header__actions\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.board-tags\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.storyboard-editor-content\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.storyboard-preview-pane\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(table).toMatch(/\.structured-table\s*{[\s\S]*width:\s*max-content;/);
    expect(table).toMatch(/\.structured-table\s*{[\s\S]*min-width:\s*1280px;/);
    expect(table).toMatch(/\.structured-table th:nth-child\(12\),[\s\S]*\.structured-table td:nth-child\(12\)\s*{[\s\S]*min-width:\s*220px;/);
    expect(table).toMatch(/\.structured-table th,[\s\S]*\.structured-table td\s*{[\s\S]*word-break:\s*normal;/);
    expect(css).not.toContain("editor-mode-switch");
  });

  it("keeps generated script tables readable instead of squeezing long English copy", () => {
    const table = readSource("../src/pages/scripts/components/ScriptStructuredPreview.vue");

    expect(table).toMatch(/\.structured-table\s*{[\s\S]*width:\s*max-content;/);
    expect(table).toMatch(/\.structured-table\s*{[\s\S]*min-width:\s*1120px;/);
    expect(table).toMatch(/\.structured-table th:nth-child\(8\),[\s\S]*\.structured-table td:nth-child\(8\)\s*{[\s\S]*min-width:\s*200px;/);
    expect(table).toMatch(/\.structured-table th,[\s\S]*\.structured-table td\s*{[\s\S]*word-break:\s*normal;/);
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

    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*width:\s*100%;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*overflow:\s*hidden;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*container-name:\s*editing-workspace;/);
    expect(css).not.toContain("height: 400px");
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(260px,\s*34vh\);/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*gap:\s*var\(--space-3\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(270px,\s*330px\)\s+minmax\(520px,\s*1fr\)\s+minmax\(280px,\s*340px\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*gap:\s*var\(--space-3\);/);
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*flex:\s*1\s+1\s+auto;/);
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*min-height:\s*0;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*330px\)\s+minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;[\s\S]*min-height:\s*180px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*auto\s+auto\s+minmax\(260px,\s*36vh\);[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
  });
});
