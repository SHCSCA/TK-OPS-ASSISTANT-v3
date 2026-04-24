import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

function readBetween(source: string, start: string, end: string) {
  const startIndex = source.indexOf(start);
  const endIndex = source.indexOf(end, startIndex + start.length);
  expect(startIndex).toBeGreaterThanOrEqual(0);
  expect(endIndex).toBeGreaterThan(startIndex);
  return source.slice(startIndex, endIndex);
}

describe("shell layout contract", () => {
  it("locks the root webview to the viewport without browser scrollbars", () => {
    const shellCss = readSource("../src/styles/shell.css");
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(shellCss).toMatch(/html,\s*body,\s*#app\s*{[\s\S]*margin:\s*0;/);
    expect(shellCss).toMatch(/html,\s*body,\s*#app\s*{[\s\S]*overflow:\s*hidden;/);
    expect(shellCss).toMatch(/html,\s*body,\s*#app\s*{[\s\S]*height:\s*100%;/);

    expect(appShell).not.toContain("width: 100vw;");
    expect(appShell).toMatch(/\.app-shell\s*{[\s\S]*width:\s*100%;/);
    expect(appShell).toMatch(/\.app-shell__workspace\s*{[\s\S]*overflow:\s*hidden;/);
    expect(appShell).toMatch(/\.app-shell__content\s*{[\s\S]*min-width:\s*0;/);
  });

  it("keeps title-bar metadata from overlapping window controls", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");
    const titleBar = readSource("../src/layouts/shell/ShellTitleBar.vue");

    expect(appShell).toMatch(/\.app-shell__product-position\s*{[\s\S]*display:\s*none;/);
    expect(titleBar).toMatch(/\.shell-title-bar\s*{[\s\S]*overflow:\s*hidden;/);
    expect(titleBar).toMatch(/\.shell-title-bar__right\s*{[\s\S]*min-width:\s*0;/);
    expect(titleBar).toMatch(/\.shell-title-bar__right\s*{[\s\S]*overflow:\s*hidden;/);
    expect(titleBar).toMatch(/\.shell-window-controls\s*{[\s\S]*flex:\s*0 0 auto;/);
    expect(titleBar).toMatch(/\.status-text\s*{[\s\S]*text-overflow:\s*ellipsis;/);
  });

  it("keeps a title-bar sidebar entry visible when the rail becomes a drawer", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");
    const titleBar = readSource("../src/layouts/shell/ShellTitleBar.vue");

    expect(appShell).toContain(':show-sidebar-toggle="showWorkspaceChrome"');
    expect(titleBar).toContain('showSidebarToggle: boolean;');
    expect(titleBar).toContain('v-if="showSidebarToggle"');
    expect(titleBar).toContain('class="shell-title-bar__sidebar-toggle icon-button"');
    expect(titleBar).toContain('@click="emit(\'toggle-sidebar\')"');
    expect(titleBar).toMatch(/\.shell-title-bar__sidebar-toggle\s*{[\s\S]*display:\s*none;/);
    expect(titleBar).toMatch(/@media\s*\(max-width:\s*960px\)\s*{[\s\S]*\.shell-title-bar__sidebar-toggle\s*{[\s\S]*display:\s*flex;/);
  });

  it("replaces the top search with a detail-panel toggle entry", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");
    const titleBar = readSource("../src/layouts/shell/ShellTitleBar.vue");

    expect(titleBar).not.toContain("shell-search");
    expect(titleBar).not.toContain("搜索项目 / 脚本 / 任务 / 资产");
    expect(appShell).toContain(':show-detail-toggle="showDetailToggle"');
    expect(titleBar).toContain("showDetailToggle: boolean;");
    expect(titleBar).toContain('v-if="showDetailToggle"');
    expect(titleBar).toContain('class="shell-title-bar__detail-toggle icon-button"');
    expect(titleBar).toContain('@click="emit(\'toggle-detail\')"');
    expect(titleBar).toContain("right_panel_open");
    expect(titleBar).toContain("right_panel_close");
  });

  it("uses the shared TK-OPS brand mark instead of the old blue blocks", () => {
    const titleBar = readSource("../src/layouts/shell/ShellTitleBar.vue");
    const sidebar = readSource("../src/layouts/shell/ShellSidebar.vue");

    expect(titleBar).toContain("TkopsBrandMark");
    expect(sidebar).toContain("TkopsBrandMark");
    expect(titleBar).not.toContain("shell-brand__logo");
    expect(sidebar).not.toContain("shell-sidebar__avatar");
    expect(titleBar).not.toContain("var(--gradient-ai-primary)");
    expect(sidebar).not.toContain("var(--gradient-ai-primary)");
  });

  it("preserves the collapsed sidebar width at compact desktop breakpoints", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(appShell).toContain(':data-sidebar-effective-collapsed="String(effectiveSidebarCollapsed)"');
    expect(appShell).not.toMatch(
      /\.app-shell__workspace,\s*\.app-shell\[data-sidebar-collapsed="true"\]\s+\.app-shell__workspace\s*{\s*grid-template-columns:\s*var\(--sidebar-width-expanded\)\s+minmax\(0,\s*1fr\);/
    );
    expect(appShell).toMatch(
      /@media\s*\(max-width:\s*1440px\)\s*{[\s\S]*\.app-shell\[data-sidebar-collapsed="true"\]\s+\.app-shell__workspace\s*{[\s\S]*grid-template-columns:\s*var\(--sidebar-width-collapsed\)\s+minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(appShell).toMatch(
      /\.app-shell\[data-sidebar-effective-collapsed="true"\]\s+\.app-shell__workspace\s*{[\s\S]*grid-template-columns:\s*var\(--sidebar-width-collapsed\)\s+minmax\(0,\s*1fr\)\s+auto;/
    );
  });

  it("protects the main workspace when a desktop detail panel is open", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(appShell).toContain("const shouldProtectWorkspace = computed");
    expect(appShell).toContain("const effectiveSidebarCollapsed = computed");
    expect(appShell).toContain(':is-collapsed="effectiveSidebarCollapsed"');
    expect(appShell).toContain('@toggle-sidebar="handleToggleSidebar"');
    expect(appShell).toContain("function handleToggleSidebar()");
    expect(appShell).toContain("shellUiStore.closeDetailPanel()");
    expect(appShell).toMatch(
      /shouldProtectWorkspace[\s\S]*showWorkspaceChrome\.value[\s\S]*isDetailPanelOpen\.value[\s\S]*isConstrainedShell\.value/
    );
  });

  it("docks side panels on desktop so they do not cover the workspace", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");
    const sidebar = readSource("../src/layouts/shell/ShellSidebar.vue");
    const spacing = readSource("../src/styles/tokens/spacing.css");
    const desktop1440 = readBetween(appShell, "@media (max-width: 1440px)", "@media (max-width: 1199px)");
    const desktop1199 = readBetween(appShell, "@media (max-width: 1199px)", "@media (max-width: 960px)");
    const compact960 = readBetween(appShell, "@media (max-width: 960px)", "</style>");

    expect(appShell).toContain(':data-detail-presentation="detailPresentation"');
    expect(appShell).toContain("const detailPresentation = computed");
    expect(appShell).toMatch(/\.app-shell__sidebar\s*{[\s\S]*grid-column:\s*1;/);
    expect(appShell).toMatch(/\.app-shell__content\s*{[\s\S]*grid-column:\s*2;/);
    expect(appShell).not.toContain('[data-detail-open="true"][data-sidebar-collapsed="false"]');
    expect(desktop1440).not.toContain("position: absolute;");
    expect(desktop1440).toMatch(
      /\.app-shell__workspace\s*{[\s\S]*grid-template-columns:\s*var\(--sidebar-width-expanded\)\s+minmax\(0,\s*1fr\)\s+auto;[\s\S]*\.app-shell\[data-sidebar-collapsed="true"\]\s+\.app-shell__workspace\s*{[\s\S]*grid-template-columns:\s*var\(--sidebar-width-collapsed\)\s+minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(desktop1440).toMatch(
      /\.app-shell\[data-sidebar-effective-collapsed="true"\]\s+\.app-shell__workspace\s*{[\s\S]*grid-template-columns:\s*var\(--sidebar-width-collapsed\)\s+minmax\(0,\s*1fr\)\s+auto;/
    );
    expect(desktop1199).not.toContain("position: absolute;");
    expect(desktop1199).toMatch(/\.app-shell__workspace\s*{[\s\S]*var\(--sidebar-width-expanded\)\s+minmax\(0,\s*1fr\)\s+auto;/);
    expect(compact960).not.toMatch(/\.app-shell__detail\s*{[\s\S]*position:\s*absolute;/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="rail"\]\s+\.app-shell__workspace\s*{[\s\S]*var\(--detail-rail-width\)/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="rail"\]\s+\.app-shell__detail\s*{[\s\S]*width:\s*var\(--detail-rail-width\)/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="focus"\]\s+\.app-shell__detail\s*{[\s\S]*grid-column:\s*1;/);
    expect(spacing).toContain("--detail-rail-width: 44px;");
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1440px\)\s*{[\s\S]*--detail-panel-width-wide:\s*420px;/);
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1199px\)\s*{[\s\S]*--detail-panel-width-wide:\s*360px;/);
    expect(sidebar).toMatch(/\.shell-sidebar\[data-collapsed="true"\]\s+\.shell-sidebar__nav\s*{[\s\S]*scrollbar-width:\s*none;/);
  });
});
