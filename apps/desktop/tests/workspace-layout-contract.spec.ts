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
      /\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(420px,\s*1fr\)\s+284px;/
    );
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*gap:\s*10px;/);
    expect(css).toMatch(
      /\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(270px,\s*330px\)\s+minmax\(520px,\s*1fr\)\s+minmax\(280px,\s*340px\);/
    );
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*gap:\s*10px;/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;/);
    expect(css).toMatch(/\.workspace-timeline-area\s*{[\s\S]*background:\s*#0f1722;/);
    expect(css).toContain(".workspace-timeline-area :deep(.workspace-timeline-toolbar)");
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*330px\)\s+minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;[\s\S]*min-height:\s*220px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(284px,\s*38vh\);/);
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
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const timeline = readSource("../src/modules/workspace/WorkspaceTimeline.vue");

    expect(page).toMatch(/<div\s+class="workspace-timeline-area">[\s\S]*<WorkspaceTimelineToolbar[\s\S]*<WorkspaceTimeline/);
    expect(page).toContain(':can-delete="canDeleteSelectedClip"');
    expect(page).toContain(':can-move="canMoveSelectedClip"');
    expect(page).toContain(':can-split="canSplitSelectedClip"');
    expect(page).toContain(':can-trim="canTrimSelectedClip"');
    expect(page).toContain('@delete="handleDeleteSelectedClip"');
    expect(page).toContain('@move="handleMoveSelectedClip"');
    expect(page).toContain('@split="handleSplitSelectedClip"');
    expect(page).toContain('@trim="handleTrimSelectedClip"');
    expect(page).toContain(':playhead-ms="playheadMs"');
    expect(page).toContain('@playhead="handleSetPlayhead"');
    expect(page).toContain('@trim="handleTimelineTrim"');
    const toolBarStatusBlock = page.match(/const toolBarStatus = computed\(\(\) => \{[\s\S]*?\n\}\);/)?.[0] ?? "";
    expect(toolBarStatusBlock).toContain('return "选择工具 · 磁吸开启";');
    expect(toolBarStatusBlock).not.toContain("selectedClip.value");
    expect(timeline).toContain("buildTimelineRows");
    expect(timeline).toContain("TimelineClipView");
    expect(timeline).toContain("computePlayheadPercent");
    expect(timeline).toMatch(
      /<div\s+v-else\s+class="workspace-timeline__body">[\s\S]*<article[\s\S]*v-for="row in rows"[\s\S]*<button[\s\S]*v-for="clipView in row\.clips"/
    );
    expect(timeline).toMatch(
      /<button[\s\S]*v-for="clipView in row\.clips"[\s\S]*:style="clipStyle\(clipView\)"[\s\S]*@click\.stop="\$emit\('select-clip',\s*\{\s*clipId:\s*clipView\.id,\s*trackId:\s*row\.id\s*\}\)"/
    );
    expect(timeline).toMatch(
      /<div[\s\S]*class="workspace-timeline__playhead"[\s\S]*data-testid="workspace-playhead"[\s\S]*:style="\{\s*left:\s*`\$\{playheadPercent\}%`\s*\}"/
    );
    expect(timeline).toContain('data-testid="workspace-trim-left"');
    expect(timeline).toContain('data-testid="workspace-trim-right"');
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
    expect(timeline).toMatch(/\.workspace-timeline__tracks\s*{[\s\S]*height:\s*100%;/);
    expect(timeline).toMatch(/\.workspace-track--tall\s*{[\s\S]*min-height:\s*64px;/);
    expect(timeline).toMatch(/\.workspace-track--medium\s*{[\s\S]*min-height:\s*46px;/);
    expect(timeline).toMatch(/\.workspace-track--compact\s*{[\s\S]*min-height:\s*34px;/);
    expect(timeline).toContain("workspaceTrackMetaLabel");
    expect(timeline).toContain("cleanWorkspaceText");
    expect(timeline).toContain('class="workspace-timeline__selection"');
    expect(timeline).toContain('class="workspace-timeline__selection-label"');
    expect(timeline).toContain('class="workspace-timeline__selection-meta"');
    expect(timeline).toContain("const selectedTrack = computed");
    expect(timeline).toContain("selectedClipTrackName");
    expect(timeline).toContain("formatWorkspaceClipRange(selectedClip.value.startMs, selectedClip.value.durationMs)");
    expect(timeline).toContain("workspaceStatusLabel(selectedClip.value.status)");
    expect(timeline).toMatch(/\.workspace-timeline__selection\s*{[\s\S]*min-width:\s*0;/);
    expect(timeline).toMatch(/\.workspace-timeline__selection-label\s*{[\s\S]*text-overflow:\s*ellipsis;/);
    expect(timeline).toMatch(/\.workspace-timeline__selection-meta\s*{[\s\S]*white-space:\s*nowrap;/);
  });

  it("keeps the preview phone inside the visible M05 stage", () => {
    const preview = readSource("../src/modules/workspace/WorkspacePreviewStage.vue");

    expect(preview).toMatch(
      /\.workspace-preview-stage\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(preview).toMatch(/\.workspace-preview-stage\s*{[\s\S]*overflow:\s*hidden;/);
    expect(preview).toMatch(
      /\.workspace-preview-stage__body\s*{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*minmax\(270px,\s*430px\)\s+minmax\(220px,\s*290px\);/
    );
    expect(preview).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*min-height:\s*0;/);
    expect(preview).toMatch(/\.workspace-preview-stage__phone\s*{[\s\S]*aspect-ratio:\s*9\s*\/\s*16;/);
    expect(preview).toMatch(/\.workspace-preview-stage__phone\s*{[\s\S]*height:\s*min\(100%,\s*500px\);/);
    expect(preview).toMatch(/\.workspace-preview-stage__phone\s*{[\s\S]*max-height:\s*500px;/);
    expect(preview).toContain("workspaceStatusLabel");
    expect(preview).toContain("cleanWorkspaceText");
    expect(preview).toMatch(/\.workspace-preview-stage__transport\s*{[\s\S]*grid-template-columns:/);
    expect(preview).toMatch(/\.workspace-preview-stage__transport button\s*{[\s\S]*white-space:\s*nowrap;/);
  });

  it("keeps the M05 asset rail list scrollable instead of clipping long content", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const assetRail = readSource("../src/modules/workspace/WorkspaceAssetRail.vue");

    expect(page).toContain('@select-source-clip="handleSelectClip"');
    expect(assetRail).toContain('"select-source-clip": [payload: { clipId: string; trackId: string }];');
    expect(assetRail).toContain('@click="$emit(\'select-source-clip\', { clipId: entry.id, trackId: entry.trackId })"');
    expect(assetRail).toContain('class="workspace-asset-rail__item-card"');
    expect(assetRail).toContain('class="workspace-asset-rail__source-list"');
    expect(assetRail).toContain('class="workspace-asset-rail__item-head"');
    expect(assetRail).toContain('class="workspace-asset-rail__item-main"');
    expect(assetRail).toContain('class="workspace-asset-rail__item-time"');
    expect(assetRail).toContain('class="workspace-asset-rail__item-status"');
    expect(assetRail).toContain('class="workspace-asset-card__meta"');
    expect(assetRail).toContain('class="workspace-asset-card__status"');
    expect(assetRail).toContain("sourceEntryLabel");
    expect(assetRail).toContain("sourceEntryTime");
    expect(assetRail).toMatch(
      /\.workspace-asset-rail\s*{[\s\S]*grid-template-rows:\s*auto\s+auto\s+auto\s+auto\s+minmax\(0,\s*1fr\);/
    );
    expect(assetRail).toMatch(/\.workspace-asset-rail\s*{[\s\S]*overflow:\s*hidden;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*grid-auto-rows:\s*max-content;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*min-height:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*padding:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*margin:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*list-style:\s*none;/);
    expect(assetRail).toMatch(
      /\.workspace-asset-rail__item-card\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/
    );
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-head\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-time\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-status\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-main\s+p\s*{[\s\S]*-webkit-line-clamp:\s*2;/);
    expect(assetRail).toMatch(
      /\.workspace-asset-card\s*{[\s\S]*grid-template-columns:\s*44px\s+minmax\(0,\s*1fr\);/
    );
    expect(assetRail).not.toMatch(/\.workspace-asset-card\s*{[\s\S]*grid-template-columns:\s*54px\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__meta\s*{[\s\S]*justify-content:\s*space-between;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__status\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__body\s+p\s*{[\s\S]*-webkit-line-clamp:\s*2;/);
    expect(assetRail).toContain("workspaceStatusLabel");
    expect(assetRail).toContain("formatWorkspaceClipRange");
  });

  it("keeps M05 selection details inside the workbench instead of auto-opening the global detail drawer", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");

    expect(page).toContain("shellUiStore.closeDetailPanel()");
    expect(page).not.toContain("shellUiStore.openDetailPanel()");
    expect(page).toContain("workspaceStatusLabel");
  });
});
