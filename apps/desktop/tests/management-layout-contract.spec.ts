import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("management page layout contract", () => {
  it("classifies account and device pages as management pages", () => {
    const routeManifest = readSource("../src/app/router/route-manifest.ts");
    const appShell = readSource("../src/layouts/AppShell.vue");
    const overviewStatus = readSource("../src/components/shell/status/OverviewStatus.vue");

    expect(routeManifest).toMatch(
      /id:\s*routeIds\.accountManagement,[\s\S]*pageType:\s*"management"/
    );
    expect(routeManifest).toMatch(
      /id:\s*routeIds\.deviceWorkspaceManagement,[\s\S]*pageType:\s*"management"/
    );
    expect(routeManifest).toMatch(
      /id:\s*routeIds\.aiSystemSettings,[\s\S]*pageType:\s*"settings"/
    );
    expect(appShell).toContain('case "management":');
    expect(overviewStatus).toContain('case "management":');
  });

  it("lets management pages use the content host width without losing inner grid limits", () => {
    const appShell = readSource("../src/layouts/AppShell.vue");
    const accountCss = readSource("../src/pages/accounts/AccountManagementPage.css");
    const deviceCss = readSource("../src/pages/devices/DeviceWorkspaceManagementPage.css");

    expect(appShell).toContain('.app-shell[data-page-type="management"] .app-shell__content :deep(.page-container)');
    expect(appShell).toMatch(/\.app-shell\[data-page-type="editor"\][\s\S]*\.app-shell\[data-page-type="management"\][\s\S]*max-width:\s*none;/);
    expect(accountCss).toMatch(/\.page-container\s*{[\s\S]*width:\s*100%;/);
    expect(accountCss).toMatch(/\.page-container\s*{[\s\S]*min-width:\s*0;/);
    expect(accountCss).toMatch(/\.page-container\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(accountCss).toMatch(
      /\.workspace-grid\s*{[\s\S]*grid-template-columns:\s*minmax\(320px,\s*min\(30%,\s*420px\)\)\s+minmax\(0,\s*1fr\);/
    );
    expect(deviceCss).toMatch(
      /\.workspace-grid\s*{[\s\S]*grid-template-columns:\s*minmax\(320px,\s*min\(30%,\s*420px\)\)\s+minmax\(0,\s*1fr\);/
    );
  });

  it("keeps account cards, summaries, and detail metadata responsive", () => {
    const accountCss = readSource("../src/pages/accounts/AccountManagementPage.css");

    expect(accountCss).toMatch(
      /\.summary-grid\s*{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(min\(100%,\s*220px\),\s*1fr\)\);/
    );
    expect(accountCss).toMatch(
      /\.metric-grid\s*{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(180px,\s*1fr\)\);/
    );
    expect(accountCss).toMatch(
      /\.metadata-list\s*{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(220px,\s*1fr\)\);/
    );
    expect(accountCss).toMatch(/@media\s*\(max-width:\s*1280px\)\s*{[\s\S]*\.workspace-grid\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
    expect(accountCss).toMatch(/\.drawer-panel\s*{[\s\S]*width:\s*min\(420px,\s*calc\(100vw - 24px\)\);/);
  });
});
