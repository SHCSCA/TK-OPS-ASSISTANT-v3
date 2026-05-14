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
      /\.workspace-editor\s*{[\s\S]*grid-template-rows:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(220px,\s*32vh\);/
    );
    expect(css).toMatch(
      /\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(240px,\s*320px\)\s+minmax\(420px,\s*1fr\)\s+minmax\(260px,\s*340px\);/
    );
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*1180px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*300px\)\s+minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/@container\s+editing-workspace\s+\(max-width:\s*860px\)\s*{[\s\S]*\.workspace-stage\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
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
});
