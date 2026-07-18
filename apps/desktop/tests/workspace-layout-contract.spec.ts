import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("workspace layout taxonomy contract", () => {
  it("keeps desktop icon fonts local instead of relying on external Google fonts", () => {
    const index = readSource("../index.html");
    const icons = readSource("../src/styles/icons.css");
    const styles = readSource("../src/styles/index.css");
    const fontFile = readFileSync(path.resolve(process.cwd(), "src/assets/fonts/material-symbols.ttf"));

    expect(index).not.toContain("fonts.googleapis.com");
    expect(index).not.toContain("fonts.gstatic.com");
    expect(styles).toContain('@import "./icons.css";');
    expect(fontFile.byteLength).toBeGreaterThan(100_000);
    expect(icons).toContain("material-symbols.ttf");
    expect(icons).toMatch(/font-family:\s*'Material Symbols Outlined';/);
  });

  it("keeps M05 page recovery notices split out of the page shell", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const pageLines = page.split(/\r?\n/).length;

    expect(pageLines).toBeLessThanOrEqual(600);
    expect(page).toContain('import WorkspaceAICapabilityRecovery from "@/modules/workspace/WorkspaceAICapabilityRecovery.vue";');
    expect(page).toContain('import WorkspaceSourceRecovery from "@/modules/workspace/WorkspaceSourceRecovery.vue";');
    expect(page).toContain('import WorkspaceSyncRecovery from "@/modules/workspace/WorkspaceSyncRecovery.vue";');
    expect(page).toContain("<WorkspaceAICapabilityRecovery");
    expect(page).toContain("<WorkspaceSourceRecovery");
    expect(page).toContain("<WorkspaceSyncRecovery");
    expect(page).not.toContain('class="workspace-source-recovery"');
    expect(page).not.toContain('class="workspace-sync-recovery"');
    expect(page).not.toContain('class="workspace-ai-readiness-alert"');
  });

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
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const css = readSource("../src/pages/workspace/AIEditingWorkspacePage.css");
    const shellContext = readSource("../src/modules/workspace/useWorkspaceShellDetailContext.ts");
    const syncRecovery = readSource("../src/modules/workspace/WorkspaceSyncRecovery.vue");

    expect(css).toMatch(
      /\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*gap:\s*var\(--space-2\);/);
    expect(css).toMatch(/\.workspace-editor\s*{[\s\S]*overflow:\s*hidden;/);
    expect(page).toContain('class="workspace-editor"');
    expect(page).toContain('import WorkspaceEditingStatusBar from "@/modules/workspace/WorkspaceEditingStatusBar.vue";');
    expect(page).toContain("<WorkspaceEditingStatusBar");
    expect(css).toContain(".workspace-editing-status-bar");
    expect(css).toMatch(/\.workspace-editing-status-bar\s*{[\s\S]*flex:\s*0\s+0\s+auto;/);
    expect(page).not.toContain('class="workspace-editor scroll-area"');
    expect(css).toMatch(
      /\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(200px,\s*248px\)\s+minmax\(620px,\s*1fr\)\s+minmax\(200px,\s*248px\);/
    );
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(500px,\s*1\.25fr\)\s+clamp\(190px,\s*22vh,\s*230px\);/);
    expect(css).toMatch(/\.workspace-stage\s*{[\s\S]*gap:\s*var\(--space-2\);/);
    expect(css).toMatch(/\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;/);
    expect(css).toMatch(/\.workspace-timeline-area\s*{[\s\S]*background:\s*#0f1722;/);
    expect(css).toContain(".workspace-timeline-area :deep(.workspace-timeline-toolbar)");
    expect(css).not.toContain(".workspace-pop");
    expect(page).not.toContain('transition name="workspace-pop"');
    expect(css).toContain("contain: layout paint;");
    expect(css).toContain("overflow-anchor: none;");
    expect(page).toContain("同步 AI 三轨");
    expect(page).toContain('<h1 class="page-header__title">AI 剪辑工作台</h1>');
    expect(page).not.toContain('<h1 class="page-header__title">M05 AI 剪辑工作台</h1>');
    expect(page).not.toContain("汇入创作链路");
    expect(page).toContain("managedTrackSyncRecovery");
    expect(shellContext).toContain("summarizeManagedTrackSync");
    expect(syncRecovery).toContain('data-testid="workspace-sync-recovery"');
    expect(syncRecovery).toContain('data-testid="workspace-sync-managed-tracks-button"');
    expect(syncRecovery).toMatch(/\.workspace-sync-recovery\s*{[\s\S]*grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(syncRecovery).toMatch(/\.workspace-sync-recovery button\s*{[\s\S]*background:\s*var\(--color-brand-primary\);/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1160px\)/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);[\s\S]*minmax\(460px,\s*auto\)[\s\S]*clamp\(240px,\s*32vh,\s*300px\)/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*display:\s*contents;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.page-header__crumb,[\s\S]*\.page-header__subtitle\s*{[\s\S]*display:\s*none;/);
    const mediumLayoutBlock = css.match(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*?\n}/)?.[0] ?? "";
    expect(mediumLayoutBlock).not.toContain(".workspace-sync-recovery button");
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*grid-row:\s*1;[\s\S]*min-height:\s*460px;[\s\S]*overflow:\s*visible;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper \.preview-panel\s*{[\s\S]*overflow:\s*visible;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage\)\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage\)\s*{[\s\S]*overflow:\s*visible;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*300px;/);
    expect(css).not.toContain("min-height: 140px");
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__footer p\)\s*{[\s\S]*display:\s*none;/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__transport\)\s*{[\s\S]*display:\s*none;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-column:\s*1;[\s\S]*grid-row:\s*2;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.stage-panel-wrapper--asset\s*{[\s\S]*grid-column:\s*1;[\s\S]*grid-row:\s*3;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-column:\s*1;[\s\S]*grid-row:\s*4;[\s\S]*min-height:\s*112px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-timeline-area\s+:deep\(\.workspace-timeline-toolbar\)\s*{[\s\S]*overflow-x:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-editor\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*minmax\(340px,\s*auto\)[\s\S]*clamp\(230px,\s*32vh,\s*280px\)/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*display:\s*contents;/);
    expect(syncRecovery).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-sync-recovery\s*{[\s\S]*grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\);/);
    expect(syncRecovery).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-sync-recovery button\s*{[\s\S]*grid-column:\s*1\s*\/\s*-1;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*grid-row:\s*1;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-timeline-area-wrapper\s*{[\s\S]*grid-row:\s*2;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.stage-panel-wrapper--asset\s*{[\s\S]*grid-row:\s*3;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.stage-panel-wrapper--inspector\s*{[\s\S]*grid-row:\s*4;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*min-height:\s*340px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*260px;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__footer p\)\s*{[\s\S]*display:\s*none;/);
    expect(css).not.toMatch(/@media\s+\(max-height:\s*860px\)\s+and\s+\(min-width:\s*1320px\)/);
    expect(css).toMatch(/@media\s+\(max-height:\s*920px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(360px,\s*1fr\)\s+clamp\(200px,\s*23vh,\s*220px\);/);
    expect(css).toMatch(/@media\s+\(max-height:\s*920px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*300px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1320px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(460px,\s*1fr\)\s+clamp\(190px,\s*24vh,\s*230px\);/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1320px\)\s*{[\s\S]*\.page-header__subtitle\s*{[\s\S]*display:\s*none;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1320px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*420px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*780px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(160px,\s*200px\)\s+minmax\(480px,\s*1fr\)\s+minmax\(160px,\s*200px\);/);
    expect(css).toMatch(/@media\s+\(max-height:\s*780px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:\s*minmax\(340px,\s*1fr\)\s+clamp\(190px,\s*28vh,\s*220px\);/);
    expect(css).toMatch(/@media\s+\(max-height:\s*780px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(min-width:\s*1041px\)\s+and\s+\(max-width:\s*1319px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*280px;/);
    expect(css).not.toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__transport\)\s*{[\s\S]*display:\s*none;/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__compact-status\)\s*{[\s\S]*display:\s*grid;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-rows:[\s\S]*minmax\(280px,\s*36vh\)[\s\S]*clamp\(220px,\s*32vh,\s*250px\)[\s\S]*clamp\(84px,\s*13vh,\s*104px\)[\s\S]*clamp\(92px,\s*14vh,\s*116px\)/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s*{[\s\S]*min-height:\s*280px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__viewer\)\s*{[\s\S]*min-height:\s*200px;/);
    expect(css).toMatch(/@media\s+\(max-height:\s*860px\)\s*{[\s\S]*@container\s+editing-workspace\s+\(max-width:\s*1040px\)\s*{[\s\S]*\.preview-panel-wrapper\s+:deep\(\.workspace-preview-stage__compact-status\)\s*{[\s\S]*display:\s*grid;/);
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
    const timelineStyle = readSource("../src/modules/workspace/WorkspaceTimeline.css");
    const toolbar = readSource("../src/modules/workspace/WorkspaceTimelineToolbar.vue");

    expect(timeline).toContain('<style scoped src="./WorkspaceTimeline.css"></style>');
    expect(timeline).not.toContain("<style scoped>\n.workspace-timeline");
    expect(page).toMatch(/<div\s+class="workspace-timeline-area">[\s\S]*<WorkspaceTimelineToolbar[\s\S]*<WorkspaceTimeline/);
    expect(page).toContain(':can-delete="canDeleteSelectedClip"');
    expect(page).toContain(':can-move="canMoveSelectedClip"');
    expect(page).toContain(':can-move-left="canMoveSelectedClipLeft"');
    expect(page).toContain(':can-move-right="canMoveSelectedClipRight"');
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
    expect(toolBarStatusBlock).toContain("timelineActionState.value.reason");
    expect(page).toContain("evaluateTimelineClipActions");
    expect(timeline).toContain("buildTimelineRows");
    expect(timeline).toContain("useWorkspaceTimelineDrag");
    expect(timeline).toContain('"move-preview": [payload: WorkspaceTimelineMovePreview]');
    expect(timeline).toContain('"move-commit": [payload: WorkspaceTimelineMovePreview]');
    expect(timeline).toContain('"trim-preview": [payload: WorkspaceTimelineTrimPreview]');
    expect(timeline).toContain('"trim-commit": [payload: WorkspaceTimelineTrimPreview]');
    expect(timeline).toContain('"drag-cancel": [payload: WorkspaceTimelineDragPreview]');
    expect(timeline.match(/function handleMovePointerDown[\s\S]*?\n}/)?.[0] ?? "").not.toContain('emit("move-preview"');
    expect(timeline.match(/function handleTrimPointerDown[\s\S]*?\n}/)?.[0] ?? "").not.toContain('emit("trim-preview"');
    expect(timeline).toContain("@pointerdown.stop=\"handleMovePointerDown(clipView.clip, $event)\"");
    expect(timeline).toContain("@pointerdown.stop=\"handleTrimPointerDown(clipView.clip, 'left', $event)\"");
    expect(timeline).toContain("@pointerdown.stop=\"handleTrimPointerDown(clipView.clip, 'right', $event)\"");
    expect(timeline).toContain('document.addEventListener("pointermove", handleDocumentPointerMove, { passive: true })');
    expect(timeline).toContain('document.addEventListener("pointerup", handleDocumentPointerUp, { passive: true })');
    expect(timeline).not.toContain("useEditingWorkspaceStore");
    expect(timeline).not.toContain("runtimeClient");
    expect(timeline).toContain("TimelineClipView");
    expect(timeline).toContain("computePlayheadPercent");
    expect(timeline).toContain("declaredTargetDurationMs");
    expect(timeline).toContain("summarizeManagedTrackSync(props.tracks, durationMs.value, declaredTargetDurationMs.value)");
    expect(timeline).toContain('data-testid="workspace-timeline-sync-summary"');
    expect(timeline).toContain("三轨统一结束");
    expect(timeline).toContain("三轨需要同步");
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
    expect(timeline).toContain('class="workspace-track__sync-target"');
    expect(timeline).toContain("AI 统一目标");
    expect(timeline).toContain(':style="{ width: `${row.syncTargetPercent}%` }"');
    expect(timeline).toContain('class="workspace-track__sync-gap"');
    expect(timeline).toContain('row.syncGapWidthPercent > 0');
    expect(timeline).toContain("row.syncGapLeftPercent");
    expect(timeline).toMatch(
      /v-if="row\.visualClass === 'video'"[\s\S]*class="workspace-timeline__thumbnail-strip"[\s\S]*<span\s+v-for="index in 5"/
    );
    expect(timeline).toMatch(
      /v-else-if="row\.visualClass === 'voice' \|\| row\.visualClass === 'bgm'"[\s\S]*class="workspace-timeline__waveform"[\s\S]*<span\s+v-for="index in 14"/
    );
    expect(timeline).toMatch(
      /<div\s+v-else\s+class="workspace-timeline__subtitle-block">[\s\S]*\{\{\s*subtitleText\(clipView\.clip\)\s*\}\}/
    );
    expect(timelineStyle).toMatch(/\.workspace-track--video\s+\.workspace-clip\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-track--voice\s+\.workspace-clip\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-track--bgm\s+\.workspace-clip\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-track--subtitle\s+\.workspace-clip\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__tracks\s*{[\s\S]*height:\s*100%;/);
    expect(timelineStyle).toMatch(/\.workspace-track--tall\s*{[\s\S]*min-height:\s*68px;/);
    expect(timelineStyle).toMatch(/\.workspace-track--medium\s*{[\s\S]*min-height:\s*56px;/);
    expect(timelineStyle).toMatch(/\.workspace-track--compact\s*{[\s\S]*min-height:\s*44px;/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__sync-summary\s*{[\s\S]*grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\);/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__sync-summary\[data-sync="synced"\]\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__sync-summary\[data-sync="warning"\]\s*{/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-surface:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-header:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-lane:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-grid:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-sync-target-bg:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline\s*{[\s\S]*--workspace-timeline-sync-target-line:/);
    expect(timelineStyle).toMatch(/:root\[data-theme="dark"\]\s+\.workspace-timeline\s*{[\s\S]*--workspace-timeline-surface:/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__sync-end\s*{[\s\S]*width:\s*2px;/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__sync-end span\s*{[\s\S]*background:\s*var\(--workspace-timeline-sync-label-bg\);/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-target\s*{[\s\S]*z-index:\s*0;/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-target::before\s*{[\s\S]*border-top:\s*1px\s+solid/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-target::after\s*{[\s\S]*width:\s*2px;/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-span\s*{[\s\S]*z-index:\s*1;/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-gap\s*{[\s\S]*z-index:\s*1;/);
    expect(timelineStyle).toMatch(/\.workspace-track__sync-gap::before\s*{[\s\S]*repeating-linear-gradient/);
    const compactTimelineBlock = timelineStyle.match(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*?\n}/)?.[0] ?? "";
    expect(compactTimelineBlock).not.toContain(".workspace-timeline__sync-summary {\n    display: none;");
    expect(timelineStyle).toMatch(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-timeline__sync-summary small\s*{[\s\S]*display:\s*none;/);
    expect(timeline).toContain("workspaceTrackMetaLabel");
    expect(timeline).toContain("cleanWorkspaceText");
    expect(timeline).toContain('class="workspace-timeline__selection"');
    expect(timeline).toContain('class="workspace-timeline__selection-label"');
    expect(timeline).toContain('class="workspace-timeline__selection-meta"');
    expect(timeline).toContain("const selectedTrack = computed");
    expect(timeline).toContain("selectedClipTrackName");
    expect(timeline).toContain("formatWorkspaceClipRange(selectedClip.value.startMs, selectedClip.value.durationMs)");
    expect(timeline).toContain("workspaceStatusLabel(selectedClip.value.status)");
    expect(timelineStyle).toMatch(/\.workspace-timeline__selection\s*{[\s\S]*min-width:\s*0;/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__selection-label\s*{[\s\S]*text-overflow:\s*ellipsis;/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__selection-meta\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(toolbar).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1160px\)\s*{[\s\S]*\.workspace-timeline-toolbar\s*{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\);/);
    expect(toolbar).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1160px\)\s*{[\s\S]*\.workspace-timeline-toolbar__status span\s*{[\s\S]*display:\s*none;/);
    expect(toolbar).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1160px\)\s*{[\s\S]*\.workspace-timeline-toolbar__tools\s*{[\s\S]*flex-wrap:\s*nowrap;[\s\S]*overflow-x:\s*auto;/);
    expect(toolbar).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1160px\)\s*{[\s\S]*\.workspace-timeline-toolbar__button,[\s\S]*\.workspace-timeline-toolbar__zoom\s*{[\s\S]*flex:\s*0\s+0\s+auto;/);
    expect(toolbar).toContain('aria-label="时间线视图缩放状态"');
    expect(toolbar).not.toContain('aria-disabled="true"');
    expect(toolbar).toContain('data-testid="workspace-timeline-zoom-in"');
    expect(toolbar).toContain('data-testid="workspace-timeline-zoom-slider"');
    expect(timeline).toContain('data-testid="workspace-timeline-content"');
    expect(timelineStyle).toMatch(/\.workspace-timeline__viewport\s*{[\s\S]*overflow:\s*auto;/);
    expect(timelineStyle).toMatch(/\.workspace-timeline__content\s*{[\s\S]*--workspace-timeline-grid-size:/);
    expect(toolbar).toContain("100%");
  });

  it("keeps the preview canvas inside the visible M05 stage without a device shell", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const preview = readSource("../src/modules/workspace/WorkspacePreviewStage.vue");
    const previewStyle = readSource("../src/modules/workspace/WorkspacePreviewStage.css");
    const previewStyleContract = previewStyle;
    const previewContext = readSource("../src/modules/workspace/workspacePreviewContext.ts");

    expect(preview).toContain('<style scoped src="./WorkspacePreviewStage.css"></style>');
    expect(preview).not.toContain("<style scoped>\n.workspace-preview-stage");
    expect(previewStyleContract).toMatch(
      /\.workspace-preview-stage\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage\s*{[\s\S]*position:\s*relative;/);
    const headerFooterBlock = previewStyleContract.match(
      /\.workspace-preview-stage__header,[\s\S]*?\.workspace-preview-stage__footer\s*{[\s\S]*?\n}/
    )?.[0] ?? "";
    expect(headerFooterBlock).not.toContain("position: absolute;");
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage\s*{[\s\S]*overflow:\s*hidden;/);
    expect(previewStyleContract).toMatch(
      /\.workspace-preview-stage__body\s*{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/
    );
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__body\s*{[\s\S]*justify-items:\s*stretch;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__body\s*{[\s\S]*justify-self:\s*stretch;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__body\s*{[\s\S]*width:\s*100%;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*min-height:\s*clamp\(340px,\s*44vh,\s*620px\);/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*justify-self:\s*stretch;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*width:\s*100%;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage\s*{[\s\S]*--workspace-preview-canvas-bg:/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage\s*{[\s\S]*--workspace-preview-surface-border:/);
    expect(previewStyleContract).not.toContain("#020617");
    expect(previewStyleContract).not.toContain("#000000");
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__viewer\s*{[\s\S]*background:\s*var\(--workspace-preview-canvas-bg\);/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__ratio-switch\s*{/);
    expect(preview).toContain('data-testid="workspace-preview-ratio-9-16"');
    expect(preview).toContain('data-testid="workspace-preview-ratio-16-9"');
    expect(preview).toContain('data-testid="workspace-preview-canvas"');
    expect(preview).not.toContain('data-testid="workspace-preview-phone"');
    expect(preview).not.toContain("workspace-preview-stage__phone");
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*aspect-ratio:\s*var\(--workspace-preview-aspect-ratio\);/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*box-sizing:\s*border-box;/);
    expect(previewStyleContract).not.toContain("workspace-preview-stage__phone");
    expect(previewStyleContract).not.toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*border:\s*8px\s+solid\s+#080a0d;/);
    expect(previewStyleContract).not.toMatch(/\.workspace-preview-stage__screen::before\s*{/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*height:\s*min\(100%,\s*620px\);/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*border:\s*1px\s+solid\s+var\(--workspace-preview-surface-border\);/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\s*{[\s\S]*border-radius:\s*8px;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\[data-ratio="9:16"\]\s*{[\s\S]*--workspace-preview-aspect-ratio:\s*9\s*\/\s*16;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__canvas\[data-ratio="16:9"\]\s*{[\s\S]*--workspace-preview-aspect-ratio:\s*16\s*\/\s*9;/);
    expect(preview).toContain('class="workspace-preview-stage__safe-area"');
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__safe-area\s*{[\s\S]*display:\s*none;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__caption\s*{[\s\S]*z-index:\s*2;/);
    expect(preview).not.toContain("workspace-preview-stage__facts");
    expect(preview).toContain("previewContext");
    expect(previewContext).toContain("buildWorkspacePreviewContext");
    expect(previewContext).toContain("cleanWorkspaceText");
    expect(previewContext).toContain("workspaceSourceTypeLabel");
    expect(preview).not.toContain('name="preview-fade"');
    expect(previewStyleContract).not.toContain(".preview-fade");
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__transport\s*{[\s\S]*grid-template-columns:/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__transport button\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(preview).toContain('data-testid="workspace-preview-compact-status"');
    expect(preview).toContain("播放头");
    expect(previewContext).toContain("runtimePreviewErrorMessage");
    expect(preview).toContain('data-testid="workspace-preview-runtime-error"');
    expect(preview).toContain('data-testid="workspace-preview-retry"');
    expect(preview).toContain("Runtime 预览同步失败");
    expect(preview).toContain('"retry-preview": []');
    expect(page).toContain('@retry-preview="handleRetry"');
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__compact-status\s*{[\s\S]*display:\s*none;/);
    expect(previewStyleContract).toMatch(/\.workspace-preview-stage__compact-progress\s*{[\s\S]*height:\s*7px;/);
    expect(preview).toContain("const safePlayProgress = computed");
    expect(preview).toContain(':aria-valuenow="safePlayProgress"');
    expect(preview).toContain("width: safePlayProgress + '%'");
    expect(previewStyleContract).toMatch(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__viewer\s*{[\s\S]*min-height:\s*250px;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__transport\s*{[\s\S]*display:\s*none;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__compact-status\s*{[\s\S]*display:\s*grid;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage\s*{[\s\S]*grid-template-rows:\s*auto\s+minmax\(0,\s*1fr\)\s+auto;/);
    const compactPreviewHeaderBlock = previewStyleContract.match(
      /@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*?\.workspace-preview-stage__header\s*{([\s\S]*?)\n  }/
    )?.[1] ?? "";
    expect(compactPreviewHeaderBlock).not.toContain("position: absolute;");
    expect(compactPreviewHeaderBlock).not.toContain("left:");
    expect(compactPreviewHeaderBlock).not.toContain("right:");
    expect(compactPreviewHeaderBlock).not.toContain("top:");
    expect(compactPreviewHeaderBlock).not.toContain("z-index:");
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__header p\s*{[\s\S]*display:\s*none;/);
    const compactLowPreviewBlock = previewStyleContract.slice(
      previewStyleContract.indexOf("@media (max-height: 780px) and (max-width: 960px)")
    );
    const compactPreviewFooterBlock = compactLowPreviewBlock.match(
      /\.workspace-preview-stage__footer\s*{([\s\S]*?)\n  }/
    )?.[1] ?? "";
    expect(compactLowPreviewBlock).not.toContain(".workspace-preview-stage__footer {\n    display: none;");
    expect(compactPreviewFooterBlock).not.toContain("position: absolute;");
    expect(compactPreviewFooterBlock).not.toContain("bottom:");
    expect(compactPreviewFooterBlock).not.toContain("left:");
    expect(compactPreviewFooterBlock).not.toContain("right:");
    expect(compactLowPreviewBlock).toContain(".workspace-preview-stage__footer:not(:has(.workspace-preview-stage__runtime-error, .workspace-preview-stage__audio))");
    expect(compactLowPreviewBlock).toMatch(/\.workspace-preview-stage__runtime-error,[\s\S]*\.workspace-preview-stage__audio\s*{[\s\S]*display:\s*grid;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__body\s*{[\s\S]*height:\s*100%;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__viewer\s*{[\s\S]*height:\s*100%;[\s\S]*min-height:\s*220px;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__screen\s*{[\s\S]*padding:\s*10px;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__screen strong\s*{[\s\S]*font-size:\s*18px;/);
    expect(previewStyleContract).toMatch(/@media\s+\(max-height:\s*780px\)\s+and\s+\(max-width:\s*960px\)\s*{[\s\S]*\.workspace-preview-stage__caption\s*{[\s\S]*font-size:\s*14px;/);
    expect(previewStyleContract).not.toContain("clamp(140px, 20vh, 190px)");
    expect(previewStyleContract).not.toContain("max-height: 190px");
    expect(preview).toContain('data-testid="workspace-preview-media-note"');
    expect(preview).toContain("可播放素材使用播放器控件检查");
    expect(page).toContain("<WorkspaceActionStrip");
    expect(page).toContain(':export-readiness="exportReadiness"');
    expect(page).toContain(':preview-context="previewContext"');
    expect(page).toContain('<p class="panel-label">预览与校验</p>');
    expect(page).not.toContain("<span>播放器</span>");
    expect(page).not.toContain('<p class="panel-label">播放器</p>');
    expect(previewContext).not.toContain("主播放器");
  });

  it("centralizes the unsaved leave confirmation behind a replaceable helper", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const actions = readSource("../src/modules/workspace/useAIEditingWorkspaceActions.ts");

    expect(page).toContain("useAIEditingWorkspaceActions");
    expect(actions).toContain('import { requestDesktopConfirm } from "@/composables/useDesktopConfirm";');
    expect(actions).toContain("function confirmUnsavedTimelineLeave()");
    expect(actions).toContain("requestDesktopConfirm(");
    expect(actions).toContain("onBeforeRouteLeave(async () =>");
    expect(actions).toContain("return confirmUnsavedTimelineLeave();");
    expect(actions).not.toContain("window.confirm(");
  });

  it("keeps the M05 asset rail list scrollable instead of clipping long content", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const actions = readSource("../src/modules/workspace/useAIEditingWorkspaceActions.ts");
    const assetRail = readSource("../src/modules/workspace/WorkspaceAssetRail.vue");
    const handleSelectClipBlock = actions.match(/function handleSelectClip[\s\S]*?\n  }/)?.[0] ?? "";

    expect(page).toContain('@select-source-clip="handleSelectClip"');
    expect(page).toContain("useAIEditingWorkspaceActions");
    expect(handleSelectClipBlock).toContain("workspaceStore.selectTimelineClip(payload)");
    expect(handleSelectClipBlock).not.toContain("workspaceStore.selectTrack(payload.trackId)");
    expect(handleSelectClipBlock).not.toContain("workspaceStore.selectClip(payload.clipId)");
    expect(assetRail).toContain('"select-source-clip": [payload: { clipId: string; trackId: string }];');
    expect(assetRail).toContain('@click="$emit(\'select-source-clip\', { clipId: entry.id, trackId: entry.trackId })"');
    expect(assetRail).toContain(':data-testid="tab.testId"');
    expect(assetRail).toContain('testId: "workspace-asset-tab-storyboard"');
    expect(assetRail).toContain('testId: "workspace-asset-tab-voice_track"');
    expect(assetRail).toContain('testId: "workspace-asset-tab-subtitle_track"');
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
    expect(assetRail).toContain('<small :title="summaryDescription">{{ summaryDescription }}</small>');
    expect(assetRail).not.toContain('class="workspace-asset-rail__sources"');
    expect(assetRail).not.toContain('class="workspace-asset-rail__source"');
    expect(assetRail).not.toContain('<transition-group name="source-list"');
    expect(assetRail).toMatch(
      /\.workspace-asset-rail\s*{[\s\S]*grid-template-rows:\s*auto\s+auto\s+auto\s+auto\s+minmax\(0,\s*1fr\);/
    );
    expect(assetRail).toMatch(/\.workspace-asset-rail\s*{[\s\S]*gap:\s*10px;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail\s*{[\s\S]*padding:\s*14px;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail\s*{[\s\S]*overflow:\s*hidden;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__summary\s*{[\s\S]*grid-template-columns:\s*auto\s+minmax\(0,\s*1fr\);/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__summary\s*{[\s\S]*padding:\s*8px\s+10px;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__summary small\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*grid-auto-rows:\s*max-content;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*min-height:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__list--sources\s*{[\s\S]*grid-row:\s*1\s*\/\s*-1;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*padding:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*margin:\s*0;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__source-list\s*{[\s\S]*list-style:\s*none;/);
    expect(assetRail).toMatch(
      /\.workspace-asset-rail__item-card\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/
    );
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-head\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-time\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-status\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-card\s*{[\s\S]*padding:\s*10px\s+12px;/);
    expect(assetRail).toMatch(/\.workspace-asset-rail__item-main\s+p\s*{[\s\S]*-webkit-line-clamp:\s*1;/);
    expect(assetRail).toMatch(
      /\.workspace-asset-card\s*{[\s\S]*grid-template-columns:\s*minmax\(86px,\s*36%\)\s+minmax\(0,\s*1fr\);/
    );
    expect(assetRail).not.toMatch(/\.workspace-asset-card\s*{[\s\S]*grid-template-columns:\s*54px\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(assetRail).toContain('class="workspace-asset-card__preview"');
    expect(assetRail).toContain('class="workspace-asset-card__waveform"');
    expect(assetRail).toMatch(/\.workspace-asset-card__thumbnail\s*{[\s\S]*aspect-ratio:\s*16\s*\/\s*10;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__thumbnail\s*{[\s\S]*overflow:\s*hidden;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__meta\s*{[\s\S]*justify-content:\s*space-between;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__status\s*{[\s\S]*white-space:\s*nowrap;/);
    expect(assetRail).toMatch(/\.workspace-asset-card__body\s+p\s*{[\s\S]*-webkit-line-clamp:\s*2;/);
    expect(assetRail).toContain("workspaceStatusLabel");
    expect(assetRail).toContain("formatWorkspaceClipRange");
  });

  it("keeps M05 selection details inside the workbench instead of auto-opening the global detail drawer", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const shellContext = readSource("../src/modules/workspace/useWorkspaceShellDetailContext.ts");

    expect(page).toContain("useWorkspaceShellDetailContext");
    expect(shellContext).toContain("shellUiStore.closeDetailPanel()");
    expect(shellContext).not.toContain("shellUiStore.openDetailPanel()");
    expect(shellContext).toContain("workspaceStatusLabel");
    expect(page).toContain(':preview-context="previewContext"');
    expect(page).toContain('@focus-precheck-issue="handleFocusPrecheckIssue"');
  });

  it("wires magic cut suggestions through store, page and inspector without Runtime fetch in components", () => {
    const page = readSource("../src/pages/workspace/AIEditingWorkspacePage.vue");
    const inspector = readSource("../src/modules/workspace/WorkspaceInspector.vue");
    const suggestions = readSource("../src/modules/workspace/WorkspaceMagicCutSuggestions.vue");

    expect(page).toContain(":magic-cut-suggestion=\"magicCutSuggestion\"");
    expect(page).toContain(":magic-cut-suggestion-status=\"magicCutSuggestionStatus\"");
    expect(page).toContain('@apply-magic-cut-suggestion="handleApplyMagicCutSuggestion"');
    expect(page).toContain('@dismiss-magic-cut-suggestion="handleDismissMagicCutSuggestion"');
    expect(page).toContain('@focus-magic-cut-suggestion="handleFocusMagicCutSuggestion"');
    expect(page).toContain('@reload-magic-cut-suggestion="handleReloadMagicCutSuggestion"');
    expect(page).toContain('@regenerate-magic-cut-suggestion="handleMagicCut"');
    expect(page).toContain("workspaceStore.applyMagicCutSuggestion(operationIds)");
    expect(page).toContain("workspaceStore.dismissMagicCutSuggestion()");
    expect(page).toContain("workspaceStore.loadMagicCutSuggestion()");
    expect(inspector).toContain('import WorkspaceMagicCutSuggestions from "./WorkspaceMagicCutSuggestions.vue";');
    expect(inspector).toContain("<WorkspaceMagicCutSuggestions");
    expect(inspector).not.toContain("fetch(");
    expect(inspector).not.toContain("requestRuntime");
    expect(suggestions).not.toContain("fetch(");
    expect(suggestions).not.toContain("requestRuntime");
    expect(suggestions).toContain('data-testid="magic-cut-regenerate"');
    expect(suggestions).toContain('data-testid="magic-cut-operation-list"');
    expect(suggestions).toContain('data-testid="magic-cut-bulk-actions"');
    expect(suggestions).toMatch(/\.workspace-magic-cut-suggestions__actions\s*{[\s\S]*flex-wrap:\s*wrap;/);
    expect(suggestions).toMatch(/\.workspace-magic-cut-suggestions__list\s*{[\s\S]*overflow-y:\s*auto;/);
    expect(suggestions).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*420px\)/);
  });

  it("uses current magic_cut delivery wording in the AI action bar", () => {
    const aiActions = readSource("../src/modules/workspace/WorkspaceAIActions.vue");
    const noteBlock = aiActions.match(/const note = computed\(\(\) => \{[\s\S]*?\n\}\);/)?.[0] ?? "";

    expect(aiActions).not.toContain("AI 魔法剪");
    expect(aiActions).not.toContain('"Blocked"');
    expect(aiActions).not.toContain('"Disabled"');
    expect(aiActions).not.toContain('"Ready"');
    expect(aiActions).not.toContain("blocked / disabled");
    expect(aiActions).not.toContain("返回 blocked");
    expect(aiActions).not.toContain("命令保持 disabled");
    expect(aiActions).toContain("智能粗剪");
    expect(aiActions).toContain("已阻断");
    expect(aiActions).toContain("处理中");
    expect(aiActions).toContain("等待时间线");
    expect(aiActions).toContain("可用");
    expect(noteBlock).toMatch(/if \(props\.blockedMessage\) return props\.blockedMessage;[\s\S]*if \(!props\.hasTimeline\)/);
  });
});
