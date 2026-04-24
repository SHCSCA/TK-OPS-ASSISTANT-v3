import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("device workspace layout contract", () => {
  it("uses density tokens instead of fixed large page padding", () => {
    const spacing = readSource("../src/styles/tokens/spacing.css");
    const deviceCss = readSource("../src/pages/devices/DeviceWorkspaceManagementPage.css");

    expect(spacing).toMatch(/--density-page-padding-x:\s*var\(--space-8\);/);
    expect(spacing).toMatch(/--density-panel-gap:\s*var\(--space-4\);/);
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1440px\)\s*{[\s\S]*--density-page-padding-x:\s*var\(--space-6\);/);
    expect(spacing).toMatch(/@media\s*\(max-width:\s*1199px\)\s*{[\s\S]*--density-page-padding-x:\s*var\(--space-4\);/);

    expect(deviceCss).toMatch(/\.page-container\s*{[\s\S]*width:\s*100%;/);
    expect(deviceCss).toMatch(/\.page-container\s*{[\s\S]*min-width:\s*0;/);
    expect(deviceCss).toMatch(/\.page-container\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(deviceCss).toMatch(/\.page-container\s*{[\s\S]*padding:\s*var\(--density-page-padding-y\)\s+var\(--density-page-padding-x\)/);
    expect(deviceCss).not.toMatch(/\.page-container\s*{[\s\S]*padding:\s*var\(--space-6\)\s+var\(--space-8\)/);
  });

  it("keeps device content from forcing horizontal scroll in compact desktop", () => {
    const deviceCss = readSource("../src/pages/devices/DeviceWorkspaceManagementPage.css");
    const shellCss = readSource("../src/styles/shell.css");
    const appShell = readSource("../src/layouts/AppShell.vue");

    expect(shellCss).toMatch(/\.command-content-host\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(appShell).toMatch(/\.app-shell__content\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(deviceCss).toMatch(
      /\.workspace-grid\s*{[\s\S]*grid-template-columns:\s*minmax\(280px,\s*min\(34%,\s*360px\)\)\s+minmax\(0,\s*1fr\);/
    );
    expect(deviceCss).toMatch(/@media\s*\(max-width:\s*1320px\)\s*{[\s\S]*\.workspace-grid\s*{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\);/);
    expect(deviceCss).toMatch(/\.detail-metadata\s*{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(220px,\s*1fr\)\);/);
    expect(deviceCss).toMatch(/\.detail-metadata dd\s*{[\s\S]*overflow-wrap:\s*anywhere;/);
    expect(deviceCss).toMatch(/\.drawer-panel\s*{[\s\S]*width:\s*min\(420px,\s*calc\(100vw - 24px\)\);/);
  });
});
