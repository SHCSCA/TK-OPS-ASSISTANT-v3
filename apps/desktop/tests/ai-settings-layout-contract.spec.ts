import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

function readSource(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

describe("AI settings layout contract", () => {
  it("uses Tauri directory picker without browser prompt fallback", () => {
    const helpers = readSource("../src/pages/settings/ai-system-settings-page-helpers.ts");

    expect(helpers).toContain('import("@tauri-apps/plugin-dialog")');
    expect(helpers).not.toContain("@vite-ignore");
    expect(helpers).not.toContain("window.prompt");
    expect(helpers).not.toContain("请输入本地目录路径");
    expect(helpers).toContain("当前环境无法打开系统目录选择器");
  });

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
    const settingsPage = readSource("../src/pages/settings/AISystemSettingsPage.vue");
    const sectionRail = readSource("../src/modules/settings/components/SettingsSectionRail.vue");

    expect(settingsPage).not.toContain("SettingsDiagnosticPanel");
    expect(settingsPage).not.toContain('data-testid="settings-inline-diagnostics"');
    expect(settingsPage).not.toContain("currentSection === 'diagnostics'");
    expect(sectionRail).not.toContain("诊断工作台");
    expect(sectionRail).not.toContain("diagnostics");
    expect(settingsPage).not.toContain("打开右侧抽屉");
    expect(settingsPage).not.toContain("切换属性面板");
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*width:\s*100%;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*container-name:\s*settings-console;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*container-type:\s*inline-size;/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*max-width:\s*var\(--density-page-max-width\);/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*padding:\s*var\(--density-page-padding-y\)\s+var\(--density-page-padding-x\)/);
    expect(settingsCss).toMatch(/\.settings-console\s*{[\s\S]*overflow-x:\s*hidden;/);
    expect(settingsCss).toMatch(
      /\.settings-console__workspace-header h2\s*{[\s\S]*font:\s*var\(--font-title-lg\);/
    );
    expect(settingsCss).not.toContain(".settings-console__workspace-actions .settings-page__button");
    expect(sectionRail).toMatch(
      /\.settings-section-rail__item\s*{[\s\S]*min-height:\s*36px;/
    );
  });

  it("downgrades settings page sections by actual content width", () => {
    const settingsCss = readSource("../src/pages/settings/AISystemSettingsPage.css");

    expect(settingsCss).toMatch(
      /\.settings-console__body\s*{[\s\S]*grid-template-columns:\s*220px\s+minmax\(0,\s*1fr\);/
    );
    expect(settingsCss).not.toContain(".settings-console__inspector");
    expect(settingsCss).not.toContain("settings-console__diagnostic");
    expect(settingsCss).toMatch(
      /@container\s+settings-console\s+\(max-width:\s*900px\)\s*{[\s\S]*\.settings-console__body,[\s\S]*\.settings-console__capability-layout\s*{[\s\S]*grid-template-columns:\s*1fr;/
    );
    expect(settingsCss).toMatch(
      /@container\s+settings-console\s+\(max-width:\s*900px\)\s*{[\s\S]*\.settings-console__workspace-header\s*{[\s\S]*flex-direction:\s*column;/
    );
    expect(settingsCss).not.toContain(".settings-console__workspace-actions,");
  });

  it("uses object list, workspace, and inspector layouts for settings sections", () => {
    const systemPanel = readSource("../src/modules/settings/components/SettingsSystemFormPanel.vue");
    const providerPanel = readSource("../src/modules/settings/components/ProviderCatalogPanel.vue");
    const capabilityMatrix = readSource("../src/modules/settings/components/AICapabilityMatrix.vue");
    const capabilityInspector = readSource("../src/modules/settings/components/AICapabilityInspector.vue");

    expect(systemPanel).toContain("system-bus-layout");
    expect(systemPanel).toContain("system-directory-table");
    expect(providerPanel).toContain("provider-hub-layout");
    expect(providerPanel).toContain("provider-connected-list");
    expect(providerPanel).toContain("provider-template-library");
    expect(providerPanel).toContain("provider-model-directory");
    expect(providerPanel).toContain("provider-credential-inspector");
    expect(providerPanel).toContain("MODEL_PAGE_SIZE = 10");
    expect(providerPanel).toContain('data-field="provider.model.search"');
    expect(providerPanel).toContain('data-field="provider.model.capability"');
    expect(providerPanel).toContain('data-action="provider.model.next-page"');
    expect(providerPanel).toContain("capabilityLabel");
    expect(providerPanel).not.toContain("provider-catalog-card");
    expect(capabilityMatrix).toContain("capability-matrix__list");
    expect(capabilityMatrix).toContain("capability-matrix__row");
    expect(capabilityInspector).toContain("capability-strategy-inspector");
    expect(capabilityInspector).toContain("capability-binding-preview");
  });

  it("stacks capability rows by card width instead of viewport width", () => {
    const capabilityMatrix = readSource("../src/modules/settings/components/AICapabilityMatrix.vue");

    expect(capabilityMatrix).toMatch(/\.settings-workspace-panel\s*{[\s\S]*container-type:\s*inline-size;/);
    expect(capabilityMatrix).toMatch(
      /@container\s+\(max-width:\s*620px\)\s*{[\s\S]*\.capability-matrix__row\s*{[\s\S]*grid-template-columns:\s*1fr;/
    );
    expect(capabilityMatrix).toMatch(
      /@container\s+\(max-width:\s*620px\)\s*{[\s\S]*\.capability-matrix__meta\s*{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/
    );
    expect(capabilityMatrix).toMatch(
      /@container\s+\(max-width:\s*620px\)\s*{[\s\S]*\.capability-matrix__toggle\s*{[\s\S]*justify-self:\s*start;/
    );
  });
});
