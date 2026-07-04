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
    const table = readSource("../src/pages/storyboards/components/StoryboardSegmentedTable.vue");

    expect(css).toMatch(/\.page-header__actions\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.board-tags\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(css).toMatch(/\.storyboard-editor-content\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.storyboard-preview-pane\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(table).toMatch(/\.storyboard-segmented-table table\s*{[\s\S]*width:\s*max-content;/);
    expect(table).toMatch(/\.storyboard-segmented-table table\s*{[\s\S]*min-width:\s*1380px;/);
    expect(table).toMatch(/\.storyboard-segmented-table td:nth-child\(12\),[\s\S]*\.storyboard-segmented-table th:nth-child\(12\)\s*{[\s\S]*min-width:\s*210px;/);
    expect(table).toMatch(/\.storyboard-segmented-table th,[\s\S]*\.storyboard-segmented-table td\s*{[\s\S]*word-break:\s*normal;/);
    expect(table).toMatch(/\.storyboard-segmented-table__cell-text\s*{[\s\S]*-webkit-line-clamp:\s*4;/);
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
    expect(css).toMatch(
      /\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(css).toMatch(/\.workspace-editing-status-bar\s*{[\s\S]*flex:\s*0\s+0\s+auto;/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*gap:\s*var\(--space-2\);/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*overflow:\s*hidden;/);
    expect(css).toContain("overflow-anchor: none;");
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(200px,\s*248px\)\s+minmax\(620px,\s*1fr\)\s+minmax\(200px,\s*248px\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(500px,\s*1\.25fr\)\s+clamp\(190px,\s*22vh,\s*230px\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*gap:\s*var\(--space-2\);/);
    expect(css).toMatch(/\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;/);
    expect(css).toMatch(/\.workspace-timeline-area\s*{[\s\S]*background:\s*#0f1722;/);
    expect(css).toContain(".workspace-timeline-area :deep(.workspace-timeline-toolbar)");
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*flex:\s*1\s+1\s+auto;/);
    expect(css).toMatch(/\.stage-panel\s*{[\s\S]*min-height:\s*0;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);[\s\S]*minmax\(460px,\s*auto\)[\s\S]*clamp\(240px,\s*32vh,\s*300px\)/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*display:\s*contents;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.page-header__crumb,[\s\S]*\.page-header__subtitle\s*{[\s\S]*display:\s*none;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*grid-row:\s*1;[\s\S]*min-height:\s*460px;[\s\S]*overflow:\s*visible;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*300px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__transport\)\s*{[\s\S]*display:\s*none;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__compact-status\)\s*{[\s\S]*display:\s*grid;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:[\s\S]*minmax\(280px,\s*36vh\)[\s\S]*clamp\(220px,\s*32vh,\s*250px\)/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*min-height:\s*280px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*200px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-column:\s*1;[\s\S]*grid-row:\s*2;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-column:\s*1;[\s\S]*grid-row:\s*4;[\s\S]*min-height:\s*112px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*minmax\(340px,\s*auto\)[\s\S]*clamp\(230px,\s*32vh,\s*280px\)/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*display:\s*contents;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*grid-row:\s*1;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-row:\s*2;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*min-height:\s*340px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*260px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*780px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(160px,\s*200px\)\s+minmax\(480px,\s*1fr\)\s+minmax\(160px,\s*200px\);/);
    expect(css).toMatch(/@media\s+\(max-height:\s*780px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(340px,\s*1fr\)\s+clamp\(190px,\s*28vh,\s*220px\);/);
    expect(css).not.toMatch(/@media\s+\(max-height:\s*860px\)\s+and\s+\(min-width:\s*1320px\)/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1320px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(200px,\s*236px\)\s+minmax\(560px,\s*1fr\)\s+minmax\(200px,\s*236px\);/);
    expect(css).not.toContain("min-height: 140px");
  });
});
