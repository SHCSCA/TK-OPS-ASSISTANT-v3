import type { AppSettings, AppSettingsUpdateInput } from "@/types/runtime";

export function createBootstrapSettingsInput(): AppSettingsUpdateInput {
  return {
    scope: "bootstrap",
    runtime: {
      mode: "",
      workspaceRoot: ""
    },
    paths: {
      cacheDir: "",
      exportDir: "",
      logDir: ""
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "",
      model: "",
      voice: "",
      subtitleMode: ""
    }
  };
}

export function applySettingsToBootstrapForm(
  target: AppSettingsUpdateInput,
  source: AppSettings
): void {
  target.scope = source.scope || "bootstrap";
  target.runtime.mode = source.runtime.mode;
  target.runtime.workspaceRoot = source.runtime.workspaceRoot;
  target.paths.cacheDir = source.paths.cacheDir;
  target.paths.exportDir = source.paths.exportDir;
  target.paths.logDir = source.paths.logDir;
  target.logging.level = source.logging.level;
  target.ai.provider = source.ai.provider;
  target.ai.model = source.ai.model;
  target.ai.voice = source.ai.voice;
  target.ai.subtitleMode = source.ai.subtitleMode;
}

export function cloneBootstrapSettingsInput(
  source: AppSettingsUpdateInput
): AppSettingsUpdateInput {
  return {
    scope: source.scope || "bootstrap",
    runtime: {
      mode: source.runtime.mode,
      workspaceRoot: source.runtime.workspaceRoot
    },
    paths: {
      cacheDir: source.paths.cacheDir,
      exportDir: source.paths.exportDir,
      logDir: source.paths.logDir
    },
    logging: {
      level: source.logging.level
    },
    ai: {
      provider: source.ai.provider,
      model: source.ai.model,
      voice: source.ai.voice,
      subtitleMode: source.ai.subtitleMode
    }
  };
}

export function hasCompletedBootstrapInitialization(
  settings: AppSettings | null
): boolean {
  if (!settings) {
    return false;
  }

  const revision = typeof settings.revision === "number" ? settings.revision : 0;
  const requiredValues = [
    settings.runtime?.workspaceRoot,
    settings.paths?.cacheDir,
    settings.paths?.exportDir,
    settings.paths?.logDir,
    settings.ai?.provider,
    settings.ai?.model,
    settings.ai?.voice,
    settings.ai?.subtitleMode
  ];

  return revision > 1 && requiredValues.every((item) => typeof item === "string" && item.trim().length > 0);
}
