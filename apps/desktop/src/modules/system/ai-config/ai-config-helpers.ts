import { RuntimeError } from "@/app/runtime-client/core";
import {
  AI_CAPABILITY_KEYS,
  type AICapabilityKey,
  type ProviderAdapterType,
  type ProviderHealthStatus
} from "@/types/runtime/ai-system";

import type {
  AIConfigUiError,
  AIPageState,
  AIPageStateDescriptor
} from "./ai-config-types";

const CAPABILITY_LABELS: Record<AICapabilityKey, string> = {
  topic_generation: "选题生成",
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  video_deconstruction: "视频拆解",
  speech_to_text: "语音转写",
  image_generation: "图像生成",
  text_to_video: "文生视频",
  image_to_video: "图生视频",
  tts: "语音合成",
  subtitle_alignment: "字幕对齐",
  asset_analysis: "资产分析",
  embedding: "知识向量化"
};

const STATE_DESCRIPTORS: Record<Exclude<AIPageState, "idle" | "ready">, AIPageStateDescriptor> = {
  loading: {
    icon: "progress_activity",
    title: "正在读取真实配置",
    description: "保留当前工作面，等待本机 Runtime 返回。"
  },
  first_use: {
    icon: "auto_awesome",
    title: "从第一项真实配置开始",
    description: "当前还没有可用对象，创建后才会进入能力路由。"
  },
  empty: {
    icon: "inbox",
    title: "暂无配置对象",
    description: "这里不会填充演示数据。"
  },
  filtered_empty: {
    icon: "filter_alt_off",
    title: "没有匹配结果",
    description: "调整筛选条件或清除筛选后重试。"
  },
  dependency_blocked: {
    icon: "link_off",
    title: "前置依赖尚未就绪",
    description: "先修复 Provider、模型能力或 Prompt 依赖。"
  },
  waiting_external: {
    icon: "pending_actions",
    title: "正在等待外部任务",
    description: "任务由 Runtime 执行，可以取消或刷新状态。"
  },
  restricted: {
    icon: "lock",
    title: "当前操作受限",
    description: "请恢复授权、账号或 Runtime 状态后再试。"
  },
  error: {
    icon: "error",
    title: "配置读取失败",
    description: "错误已记录，可重试或打开关联日志。"
  }
};

export function capabilityLabel(key: AICapabilityKey): string {
  return CAPABILITY_LABELS[key];
}

export function providerAdapterLabel(type: ProviderAdapterType): string {
  switch (type) {
    case "direct_api":
      return "Direct API";
    case "openai_compatible":
      return "OpenAI-compatible";
    case "comfyui":
      return "ComfyUI";
    case "runninghub":
      return "RunningHub";
  }
}

export function providerHealthLabel(status: ProviderHealthStatus): string {
  switch (status) {
    case "unknown":
      return "未检查";
    case "checking":
      return "检查中";
    case "ready":
      return "就绪";
    case "degraded":
      return "降级";
    case "failed":
      return "失败";
  }
}

export function stateDescriptor(state: AIPageState): AIPageStateDescriptor {
  if (state === "ready") {
    return { icon: "check_circle", title: "已就绪", description: "" };
  }
  if (state === "idle") {
    return { icon: "hourglass_empty", title: "等待加载", description: "" };
  }
  return STATE_DESCRIPTORS[state];
}

export function toAIConfigUiError(
  error: unknown,
  fallback: string
): AIConfigUiError {
  if (error instanceof RuntimeError) {
    return {
      message: error.message || fallback,
      errorCode: error.errorCode,
      logId: error.logId,
      requestId: error.requestId,
      retryable:
        error.status === 0
        || error.status >= 500
        || error.errorCode === "REVISION_CONFLICT"
    };
  }
  return {
    message:
      error instanceof Error && error.message.trim()
        ? error.message
        : fallback,
    errorCode: null,
    logId: null,
    requestId: null,
    retryable: false
  };
}

export function pageStateFromError(error: AIConfigUiError): AIPageState {
  if (
    error.errorCode === "LICENSE_INVALID"
    || error.errorCode === "LICENSE_MACHINE_MISMATCH"
    || error.errorCode === "LICENSE_STORE_UNAVAILABLE"
    || error.errorCode === "RUNTIME_SESSION_REQUIRED"
    || error.errorCode === "RUNTIME_SESSION_INVALID"
    || error.errorCode === "RUNTIME_ORIGIN_FORBIDDEN"
    || error.errorCode === "ACCOUNT_ARCHIVED"
  ) {
    return "restricted";
  }
  return "error";
}

export function createAIOperationKey(
  operation: string,
  resourceId = "system"
): string {
  const suffix =
    globalThis.crypto?.randomUUID?.()
    ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  return `${operation}:${resourceId}:${suffix}`.slice(0, 128);
}

export function parseJsonObject(
  value: string,
  label: string
): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch (error) {
    throw new Error(`${label}不是有效 JSON：${error instanceof Error ? error.message : "语法错误"}`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label}必须是 JSON 对象。`);
  }
  return parsed as Record<string, unknown>;
}

export function prettyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

export function isAICapabilityKey(value: string): value is AICapabilityKey {
  return (AI_CAPABILITY_KEYS as readonly string[]).includes(value);
}

export function logAIConfigError(message: string, error: unknown): void {
  console.error(`[ai-config] ${message}`, error);
}
