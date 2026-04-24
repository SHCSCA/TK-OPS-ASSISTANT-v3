import { openPath } from "@tauri-apps/plugin-opener";

import type { AICapabilityConfig, AppSettings, AppSettingsUpdateInput } from "@/types/runtime";

export type SettingsSectionId = "system" | "provider" | "capability" | "diagnostics";
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
    title: "集中维护 Runtime、路径和默认模型",
    summary: "运行模式、缓存目录、导出目录和默认 AI 选项都通过配置总线读写，不在页面里单独保存。"
  },
  provider: {
    eyebrow: "Provider 与模型",
    title: "管理 Provider 注册表、模型目录和连接凭据",
    summary: "注册表里的 Provider 才能进入这里，模型目录和健康检查全部走真实 Runtime 接口。"
  },
  capability: {
    eyebrow: "能力策略",
    title: "围绕能力切换 Provider、模型和提示词",
    summary: "左侧矩阵负责选中能力，右侧 Inspector 负责 Provider、模型和提示词的具体编辑。"
  },
  diagnostics: {
    eyebrow: "诊断工作台",
    title: "把诊断、状态和错误收拢到右侧抽屉",
    summary: "主区保留运行视图，右侧抽屉负责更细的诊断、连通性和错误回显。"
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
    const dialogModuleName = "@tauri-apps/plugin-dialog";
    const dialog = await import(/* @vite-ignore */ dialogModuleName);
    const selected = await dialog.open({
      defaultPath: currentValue || undefined,
      directory: true,
      multiple: false
    });
    return typeof selected === "string" ? selected : "";
  } catch {
    return window.prompt("请输入本地目录路径", currentValue)?.trim() ?? "";
  }
}

export async function openDirectoryPath(path: string): Promise<void> {
  const targetPath = path.trim();
  if (!targetPath) {
    throw new Error("请先设置日志目录。");
  }

  await openPath(targetPath);
}
