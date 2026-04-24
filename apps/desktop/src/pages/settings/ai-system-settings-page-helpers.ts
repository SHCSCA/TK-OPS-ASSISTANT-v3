import { openPath } from "@tauri-apps/plugin-opener";

import type { AICapabilityConfig, AppSettings, AppSettingsUpdateInput } from "@/types/runtime";

export type SettingsSectionId = "system" | "provider" | "capability";
export type DirectoryField =
  | "runtime.workspaceRoot"
  | "paths.cacheDir"
  | "paths.exportDir"
  | "paths.logDir";

export const capabilityLabels: Record<string, string> = {
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  tts_generation: "配音生成",
  subtitle_alignment: "字幕对齐",
  video_generation: "视频生成",
  asset_analysis: "资产分析"
};

export function capabilityLabel(capabilityId: string): string {
  return capabilityLabels[capabilityId] ?? capabilityId;
}

const runtimeStatusLabels: Record<string, string> = {
  online: "在线",
  loading: "读取中",
  offline: "离线"
};

export function runtimeStatusLabel(status: string): string {
  return runtimeStatusLabels[status] ?? "待检查";
}

const configStatusLabels: Record<string, string> = {
  loading: "配置读取中",
  saving: "配置保存中",
  ready: "配置已就绪",
  error: "配置异常"
};

export function configStatusLabel(status: string): string {
  return configStatusLabels[status] ?? "等待配置";
}

type SectionCopy = {
  eyebrow: string;
  title: string;
  summary: string;
};

const sectionCopies: Record<SettingsSectionId, SectionCopy> = {
  system: {
    eyebrow: "系统总线",
    title: "运行、路径和默认模型",
    summary: "运行模式、本地路径、日志和默认 AI 选项都通过配置总线读写。"
  },
  provider: {
    eyebrow: "Provider 与模型",
    title: "注册表、模型目录和连接凭据",
    summary: "选择 Provider 后管理模型目录、健康检查模型和真实连接凭据。"
  },
  capability: {
    eyebrow: "能力策略",
    title: "能力到 Provider 的绑定",
    summary: "先选中能力，再编辑 Provider、模型、角色和提示词策略。"
  }
};

export function sectionCopy(section: SettingsSectionId): SectionCopy {
  return sectionCopies[section];
}

export function formatErrorSummary(error: { message: string; requestId: string } | null): string {
  if (!error) {
    return "";
  }

  return error.requestId ? `${error.message}（${error.requestId}）` : error.message;
}

export function createEmptySettingsInput(): AppSettingsUpdateInput {
  return {
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

export function settingsToInput(source: AppSettings): AppSettingsUpdateInput {
  return {
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

export function applySettingsToForm(target: AppSettingsUpdateInput, source: AppSettings): void {
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

export function cloneSettingsInput(source: AppSettingsUpdateInput): AppSettingsUpdateInput {
  return {
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

export function serializeSettings(input: AppSettingsUpdateInput): string {
  return JSON.stringify(input);
}

export function serializeCapabilities(items: AICapabilityConfig[]): string {
  return JSON.stringify(
    items.map((item) => ({
      capabilityId: item.capabilityId,
      enabled: item.enabled,
      provider: item.provider,
      model: item.model,
      agentRole: item.agentRole,
      systemPrompt: item.systemPrompt,
      userPromptTemplate: item.userPromptTemplate
    }))
  );
}

export function formatDateOnly(value: string): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return date.toLocaleDateString("zh-CN");
}

export async function pickDirectoryPath(currentValue: string): Promise<string> {
  try {
    const dialog = await import("@tauri-apps/plugin-dialog");
    const selected = await dialog.open({
      defaultPath: currentValue || undefined,
      directory: true,
      multiple: false
    });
    return typeof selected === "string" ? selected : "";
  } catch {
    throw new Error("当前环境无法打开系统目录选择器，请在 TK-OPS 桌面应用中重试。");
  }
}

export async function openDirectoryPath(path: string): Promise<void> {
  const targetPath = path.trim();
  if (!targetPath) {
    throw new Error("请先设置日志目录。");
  }

  await openPath(targetPath);
}
