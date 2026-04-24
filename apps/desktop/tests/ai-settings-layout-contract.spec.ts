import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("AI settings layout contract", () => {
  it("keeps the settings overview compact and driven by typography tokens", () => {
    const statusDock = readSource("../src/modules/settings/components/SettingsStatusDock.vue");

    expect(statusDock).toMatch(/\.settings-status-dock\s*{[\s\S]*gap:\s*var\(--space-3\);/);
    expect(statusDock).toMatch(/\.settings-status-dock\s*{[\s\S]*padding:\s*var\(--space-5\);/);
    expect(statusDock).toMatch(
      /\.settings-status-dock__copy h1\s*{[\s\S]*font:\s*var\(--font-display-md\);/
    );
    expect(statusDock).toMatch(
      /\.settings-status-dock__metric\s*{[\s\S]*min-height:\s*88px;/
    );
    expect(statusDock).toMatch(
      /\.settings-status-dock__metric strong\s*{[\s\S]*font:\s*var\(--font-title-lg\);/
    );
    expect(statusDock).not.toMatch(/\.settings-status-dock__metric strong\s*{[\s\S]*font-size:/);
  });

  it("keeps the settings workspace title and actions within blueprint scale", () => {
    const settingsCss = readSource("../src/pages/settings/AISystemSettingsPage.css");
    const sectionRail = readSource("../src/modules/settings/components/SettingsSectionRail.vue");

    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*width:\s*100%;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*container-name:\s*settings-console;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*container-type:\s*inline-size;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*max-width:\s*var\(--density-page-max-width\);/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*padding:\s*var\(--density-page-padding-y\)\s+var\(--density-page-padding-x\)/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(settingsCss).toMatch(
      /\.settings-console__workspace-header h2\s*{[\s\S]*font:\s*var\(--font-title-lg\);/
    );
    expect(settingsCss).toMatch(
      /\.settings-console__workspace-actions \.settings-page__button,[\s\S]*\.settings-console__diagnostic-actions \.settings-page__button\s*{[\s\S]*min-height:\s*36px;/
    );
    expect(settingsCss).toMatch(
      /\.settings-console__workspace-actions \.settings-page__button,[\s\S]*\.settings-console__diagnostic-actions \.settings-page__button\s*{[\s\S]*white-space:\s*nowrap;/
    );
    expect(sectionRail).toMatch(
      /\.settings-section-rail__item\s*{[\s\S]*min-height:\s*36px;/
    );
  });

  it("downgrades settings page sections by actual content width", () => {
    const settingsCss = readSource("../src/pages/settings/AISystemSettingsPage.css");

    expect(settingsCss).toMatch(
      /@container\s+settings-console\s+\(max-width:\s*900px\)\s*{[\s\S]*\.settings-console__body,[\s\S]*\.settings-console__capability-layout,[\s\S]*\.settings-console__diagnostic-grid\s*{[\s\S]*grid-template-columns:\s*1fr;/
    );
    expect(settingsCss).toMatch(
      /@container\s+settings-console\s+\(max-width:\s*900px\)\s*{[\s\S]*\.settings-console__workspace-header,[\s\S]*\.settings-console__diagnostic-hero\s*{[\s\S]*flex-direction:\s*column;/
    );
    expect(settingsCss).toMatch(
      /@container\s+settings-console\s+\(max-width:\s*900px\)\s*{[\s\S]*\.settings-console__workspace-actions,[\s\S]*\.settings-console__diagnostic-actions\s*{[\s\S]*justify-content:\s*flex-start;/
    );
  });
});
