import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("workspace layout taxonomy contract", () => {
  it("uses a dedicated full-width root for the AI editing workspace", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const css = readSource("../src/pages/workspace/AIEditingWorkspacePage.css");

    expect(page).toContain('class="editing-workspace-page h-full"');
    expect(page).not.toContain('class="page-container h-full"');
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*width:\s*100%;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*height:\s*100%;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*min-width:\s*0;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*overflow:\s*hidden;/);
    expect(css).toMatch(/\.editing-workspace-page\s*{[\s\S]*container-name:\s*editing-workspace;/);
    expect(css).not.toMatch(/\.page-container\s*{[\s\S]*max-width:\s*var\(--density-page-max-width\);/);
  });

  it("keeps the M05 workbench responsive without global page max-width", () => {
    const css = readSource("../src/pages/workspace/AIEditingWorkspacePage.css");

    expect(css).toMatch(
      /\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(260px,\s*34vh\);/
    );
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*gap:\s*var\(--space-3\);/);
    expect(css).toMatch(
      /\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(270px,\s*330px\)\s+minmax\(520px,\s*1fr\)\s+minmax\(280px,\s*340px\);/
    );
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*gap:\s*var\(--space-3\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*330px\)\s+minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;[\s\S]*min-height:\s*180px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*auto\s+auto\s+minmax\(260px,\s*36vh\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
    expect(css).not.toContain(".workspace-tool-bar");
    expect(css).not.toContain(".workspace-tool-bar__actions");
  });

  it("keeps shell page-type metadata without hiding every workspace page", () => {
    const shell = readSource("../src/layouts/AppShell.vue");

    expect(shell).toContain(':data-page-type="currentPage.pageType"');
    expect(shell).not.toMatch(
      /\.app-shell\[data-page-type="workspace"\]\s+\.app-shell__content\s*{[\s\S]*overflow:\s*hidden;/
    );
  });

  it("preserves scoped layout roots for ordinary content and settings pages", () => {
    const dashboardCss = readSource("../src/pages/dashboard/CreatorDashboardPage.css");
    const settingsCss = readSource("../src/pages/settings/AISystemSettingsPage.css");

    expect(dashboardCss).toMatch(/\.page-container\s*{[\s\S]*max-width:\s*var\(--density-page-max-width\);/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*max-width:\s*min\(1680px,\s*100%\);/);
  });

  it("defines global page-width behavior by route page type", () => {
    const shell = readSource("../src/layouts/AppShell.vue");

    expect(shell).toContain('.app-shell[data-page-type="dashboard"] .app-shell__content :deep(.page-container)');
    expect(shell).toContain("max-width: min(1680px, 100%);");
    expect(shell).toContain('.app-shell[data-page-type="editor"] .app-shell__content :deep(.page-container)');
    expect(shell).toContain('.app-shell[data-page-type="workspace"] .app-shell__content :deep(.page-container)');
    expect(shell).toContain('.app-shell[data-page-type="queue"] .app-shell__content :deep(.page-container)');
    expect(shell).toContain('.app-shell[data-page-type="management"] .app-shell__content :deep(.page-container)');
    expect(shell).toContain('.app-shell[data-page-type="settings"] .app-shell__content :deep(.settings-console)');
    expect(shell).toMatch(
      /\.app-shell\[data-page-type="editor"\][\s\S]*\.app-shell\[data-page-type="management"\][\s\S]*max-width:\s*none;/
    );
    expect(shell).not.toContain('.app-shell[data-page-type="settings"] .app-shell__content :deep(.page-container)');
  });

  it("renders the M05 timeline visual contract through the view model", () => {
    const timeline = readSource("../src/modules/workspace/WorkspaceTimeline.vue");

    expect(timeline).toContain("buildTimelineRows");
    expect(timeline).toContain("TimelineClipView");
    expect(timeline).toContain("computePlayheadPercent");
    expect(timeline).toMatch(
      /<div\s+v-else\s+class="workspace-timeline__body">[\s\S]*<article[\s\S]*v-for="row in rows"[\s\S]*<button[\s\S]*v-for="clipView in row\.clips"/
    );
    expect(timeline).toMatch(
      /<button[\s\S]*v-for="clipView in row\.clips"[\s\S]*:style="clipStyle\(clipView\)"[\s\S]*@click="\$emit\('select-clip',\s*\{\s*clipId:\s*clipView\.id,\s*trackId:\s*row\.id\s*\}\)"/
    );
    expect(timeline).toMatch(
      /<div\s+class="workspace-timeline__playhead"\s+:style="\{\s*left:\s*`\$\{playheadPercent\}%`\s*\}">/
    );
    expect(timeline).toMatch(
      /v-if="row\.visualClass === 'video'"[\s\S]*class="workspace-timeline__thumbnail-strip"[\s\S]*<span\s+v-for="index in 5"/
    );
    expect(timeline).toMatch(
      /v-else-if="row\.visualClass === 'voice' \|\| row\.visualClass === 'bgm'"[\s\S]*class="workspace-timeline__waveform"[\s\S]*<span\s+v-for="index in 14"/
    );
    expect(timeline).toMatch(
      /<div\s+v-else\s+class="workspace-timeline__subtitle-block">[\s\S]*\{\{\s*subtitleText\(clipView\.clip\)\s*\}\}/
    );
    expect(timeline).toMatch(/\.workspace-track--video\s+\.workspace-clip\s*{/);
    expect(timeline).toMatch(/\.workspace-track--voice\s+\.workspace-clip\s*{/);
    expect(timeline).toMatch(/\.workspace-track--bgm\s+\.workspace-clip\s*{/);
    expect(timeline).toMatch(/\.workspace-track--subtitle\s+\.workspace-clip\s*{/);
  });
});
