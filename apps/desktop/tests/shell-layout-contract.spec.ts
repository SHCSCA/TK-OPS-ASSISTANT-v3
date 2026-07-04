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
  it("uses the UI PRD five navigation groups and hides setup from the sidebar", () => {
    const routerTypes = readSource("../src/types/router.ts");
    const routeManifest = readSource("../src/app/router/route-manifest.ts");

    const expectedGroups = ["启动与总览", "创作前置", "创作与媒体", "执行与治理", "系统与 AI"];
    expectedGroups.forEach((group) => {
      expect(routerTypes).toContain(`"${group}"`);
      expect(routeManifest).toContain(`navGroup: "${group}"`);
    });

    expect(routerTypes).toContain('"HIDDEN"');
    expect(routeManifest).toContain('id: routeIds.setupLicenseWizard');
    expect(routeManifest).toMatch(/id:\s*routeIds\.setupLicenseWizard[\s\S]*navGroup:\s*"HIDDEN"/);
    expect(routeManifest).not.toContain('"全局管理"');
    expect(routeManifest).not.toContain('"核心管线"');
  });

  it("keeps route groups aligned with PRD and UI PRD source of truth", () => {
    const routeManifest = readSource("../src/app/router/route-manifest.ts");

    expect(routeManifest).toMatch(/id:\s*routeIds\.videoDeconstructionCenter[\s\S]*navGroup:\s*"创作前置"/);
    expect(routeManifest).toMatch(/id:\s*routeIds\.renderExportCenter[\s\S]*navGroup:\s*"创作与媒体"/);
  });

  it("renders sidebar navigation groups in a fixed UI PRD order", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(appShell).toContain("NAV_GROUP_ORDER");
    expect(appShell).toMatch(
      /const NAV_GROUP_ORDER[\s\S]*"启动与总览"[\s\S]*"创作前置"[\s\S]*"创作与媒体"[\s\S]*"执行与治理"[\s\S]*"系统与 AI"/
    );
    expect(appShell).not.toContain("new Set(routeManifest.map((item) => item.navGroup))");
  });

  it("shows status bar AI and theme state without simulated latency", () => {
    const statusBar = readSource("../src/layouts/shell/ShellStatusBar.vue");

    expect(statusBar).not.toContain("128ms");
    expect(statusBar).not.toContain("'Dark'");
    expect(statusBar).not.toContain("'Light'");
    expect(statusBar).toContain("浅色");
    expect(statusBar).toContain("深色");
    expect(statusBar).toContain("AI 未配置 · 待配置");
    expect(statusBar).toContain("AI 状态未知 · Runtime 离线");
    expect(statusBar).toContain("AI 状态同步中");
    expect(statusBar).toContain("等待诊断");
  });

  it("prevents long status bar labels from overlapping in 960px compact windows", () => {
    const statusBar = readSource("../src/layouts/shell/ShellStatusBar.vue");

    expect(statusBar).toMatch(/\.status-item\s*{[\s\S]*min-width:\s*0;/);
    expect(statusBar).toMatch(/\.status-item\s+span:last-child\s*{[\s\S]*text-overflow:\s*ellipsis;/);
    expect(statusBar).toMatch(/@media\s*\(max-width:\s*960px\)\s*{[\s\S]*\.shell-status-bar__right\s+\.status-item:not\(:last-of-type\)\s*{[\s\S]*display:\s*none;/);
    expect(statusBar).not.toContain("@media (max-width: 860px)");
  });

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

    expect(appShell).toContain('window.matchMedia("(max-width: 1859px)")');
    expect(appShell).not.toContain('window.matchMedia("(max-width: 1440px)")');
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

  it("keeps the compact sidebar closed by default until the title-bar toggle opens it", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(appShell).toContain("const compactSidebarOpen = ref(false)");
    expect(appShell).toMatch(
      /const effectiveSidebarCollapsed = computed\(\(\) => \{[\s\S]*if \(isCompactDetailShell\.value\) return !compactSidebarOpen\.value;[\s\S]*return sidebarCollapsed\.value;[\s\S]*\}\);/
    );
    expect(appShell).toMatch(
      /function handleToggleSidebar\(\) \{[\s\S]*if \(isCompactDetailShell\.value\) \{[\s\S]*compactSidebarOpen\.value = !compactSidebarOpen\.value;[\s\S]*return;/
    );
    expect(appShell).toMatch(
      /watch\(\s*\(\) => route\.fullPath,[\s\S]*compactSidebarOpen\.value = false;/
    );
  });

  it("remounts the route component when the shell route changes", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(appShell).toContain('<component :is="Component" :key="route.fullPath" />');
    expect(appShell).toContain('<transition name="page-fade"');
    expect(appShell).toContain('mode="out-in"');
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
    expect(compact960).not.toMatch(/\.app-shell__detail\s*{[^}]*position:\s*absolute;/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="rail"\]\s+\.app-shell__workspace\s*{[\s\S]*var\(--detail-rail-width\)/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="rail"\]\s+\.app-shell__detail\s*{[\s\S]*width:\s*var\(--detail-rail-width\)/);
    expect(compact960).toMatch(/\.app-shell\[data-detail-presentation="focus"\]\s+\.app-shell__detail\s*{[\s\S]*grid-column:\s*1;/);
    expect(spacing).toContain("--detail-rail-width: 44px;");
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1440px\)\s*{[\s\S]*--detail-panel-width-wide:\s*420px;/);
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1199px\)\s*{[\s\S]*--detail-panel-width-wide:\s*360px;/);
    expect(sidebar).toMatch(/\.shell-sidebar\[data-collapsed="true"\]\s+\.shell-sidebar__nav\s*{[\s\S]*scrollbar-width:\s*none;/);
  });
});
