import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory } from "vue-router";
import { vi } from "vitest";

import App from "@/App.vue";
import { createAppRouter } from "@/app/router";

export function okJsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => ({
      ok: true,
      data
    })
  };
}

export function errorJsonResponse(status: number, error: string, requestId = "req-runtime") {
  return {
    ok: false,
    status,
    json: async () => ({
      ok: false,
      error,
      requestId
    })
  };
}

export const runtimeFixtures = {
  activeLicense: {
    active: true,
    restrictedMode: false,
    machineCode: "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
    machineBound: true,
    licenseType: "perpetual",
    maskedCode: "TK-O****************0001",
    activatedAt: "2026-04-11T10:00:00Z"
  },
  restrictedLicense: {
    active: false,
    restrictedMode: true,
    machineCode: "TKOPS-TEST1-TEST2-TEST3-TEST4-TEST5",
    machineBound: false,
    licenseType: "perpetual",
    maskedCode: "",
    activatedAt: null
  },
  health: {
    service: "online",
    version: "0.1.1",
    now: "2026-04-11T10:00:00Z",
    mode: "development"
  },
  providerHealth: {
    providers: [
      {
        provider: "openai",
        label: "OpenAI",
        readiness: "ready",
        lastCheckedAt: "2026-04-11T10:00:00Z",
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      },
      {
        provider: "deepseek",
        label: "DeepSeek",
        readiness: "not_configured",
        lastCheckedAt: null,
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      },
      {
        provider: "volcengine",
        label: "火山方舟",
        readiness: "not_configured",
        lastCheckedAt: null,
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      },
      {
        provider: "volcengine_tts",
        label: "火山豆包语音",
        readiness: "not_configured",
        lastCheckedAt: null,
        latencyMs: null,
        errorCode: null,
        errorMessage: null
      }
    ],
    refreshedAt: "2026-04-11T10:00:00Z"
  },
  config: {
    revision: 1,
    runtime: {
      mode: "development",
      workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
    },
    paths: {
      cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
      exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
      logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "openai",
      model: "gpt-5.4",
      voice: "zh_female_vv_uranus_bigtts",
      subtitleMode: "balanced"
    },
    media: {
      ffprobePath: ""
    }
  },
  diagnostics: {
    databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
    logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
    revision: 1,
    mode: "development",
    healthStatus: "online"
  },
  initializedConfig: {
    revision: 2,
    runtime: {
      mode: "development",
      workspaceRoot: "G:/AI/TK-OPS-ASSISTANT-V3"
    },
    paths: {
      cacheDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/cache",
      exportDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/exports",
      logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs"
    },
    logging: {
      level: "INFO"
    },
    ai: {
      provider: "openai",
      model: "gpt-5.4",
      voice: "zh_female_vv_uranus_bigtts",
      subtitleMode: "balanced"
    },
    media: {
      ffprobePath: ""
    }
  },
  initializedDiagnostics: {
    databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
    logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
    revision: 2,
    mode: "development",
    healthStatus: "online",
    configScope: "runtime_local",
    checkedAt: "2026-04-11T10:00:00Z",
    overallStatus: "warning",
    items: [
      {
        id: "media.ffprobe",
        label: "FFprobe 媒体探针",
        group: "媒体工具",
        status: "warning",
        summary: "未检测到 FFprobe，视频元数据将使用基础降级解析。",
        impact: "视频时长、分辨率、编码格式识别可能不完整。",
        detail: "来源：fallback",
        actionLabel: "准备媒体工具",
        actionTarget: "settings.media_tools.prepare"
      },
      {
        id: "runtime.health",
        label: "Runtime 服务",
        group: "基础运行",
        status: "ready",
        summary: "Runtime 在线。",
        impact: "前端可以访问本地服务。",
        detail: "online",
        actionLabel: "重新检测",
        actionTarget: "settings.diagnostics.rescan"
      }
    ]
  },
  emptyDashboardSummary: {
    recentProjects: [],
    currentProject: null
  },
  aiCapabilitySettings: {
    capabilities: [
      {
        capabilityId: "script_generation",
        enabled: true,
        provider: "openai",
        model: "gpt-5",
        agentRole: "资深短视频脚本策划",
        systemPrompt: "围绕用户主题生成高留存、可拍摄的短视频脚本。",
        userPromptTemplate: "主题：{{topic}}"
      },
      {
        capabilityId: "script_rewrite",
        enabled: true,
        provider: "openai",
        model: "gpt-5-mini",
        agentRole: "短视频脚本改写编辑",
        systemPrompt: "在保持原意的前提下提升脚本节奏、开场和转化效率。",
        userPromptTemplate: "原脚本：\\n{{script}}\\n\\n改写要求：{{instructions}}"
      },
      {
        capabilityId: "storyboard_generation",
        enabled: true,
        provider: "openai",
        model: "gpt-5-mini",
        agentRole: "分镜规划导演",
        systemPrompt: "把脚本文本拆解为清晰的镜头与视觉提示。",
        userPromptTemplate: "脚本内容：\\n{{script}}"
      },
      {
        capabilityId: "tts_generation",
        enabled: false,
        provider: "volcengine_tts",
        model: "seed-tts-2.0",
        agentRole: "配音导演",
        systemPrompt: "为脚本生成适合配音的语气和节奏说明。",
        userPromptTemplate: "脚本内容：\\n{{script}}"
      },
      {
        capabilityId: "subtitle_alignment",
        enabled: false,
        provider: "openai",
        model: "gpt-5-mini",
        agentRole: "字幕对齐编辑",
        systemPrompt: "让字幕语言和节奏更适合短视频表达。",
        userPromptTemplate: "脚本内容：\\n{{script}}"
      },
      {
        capabilityId: "video_transcription",
        enabled: false,
        provider: "openai",
        model: "whisper-1",
        agentRole: "视频拆解分析师",
        systemPrompt: "从视频素材中提取语音、字幕和内容结构。",
        userPromptTemplate: "媒体文件：\\n{{media_file}}"
      },
      {
        capabilityId: "video_generation",
        enabled: false,
        provider: "volcengine",
        model: "seedance-2.0",
        agentRole: "视频生成导演",
        systemPrompt: "把分镜转成可执行的视频生成提示。",
        userPromptTemplate: "分镜内容：\\n{{storyboard}}"
      },
      {
        capabilityId: "asset_analysis",
        enabled: false,
        provider: "volcengine",
        model: "doubao-seed-2.0-pro",
        agentRole: "素材分析师",
        systemPrompt: "总结素材内容、价值点和可复用结构。",
        userPromptTemplate: "素材内容：\\n{{assets}}"
      }
    ],
    providers: [
      {
        provider: "openai",
        label: "OpenAI",
        configured: true,
        maskedSecret: "sk-c************3456",
        baseUrl: "https://api.openai.com/v1/responses",
        secretSource: "secure_store",
        supportsTextGeneration: true
      },
      {
        provider: "deepseek",
        label: "DeepSeek",
        configured: false,
        maskedSecret: "",
        baseUrl: "https://api.deepseek.com/v1",
        secretSource: "none",
        supportsTextGeneration: true
      },
      {
        provider: "volcengine",
        label: "火山方舟",
        configured: false,
        maskedSecret: "",
        baseUrl: "https://ark.cn-beijing.volces.com/api/v3",
        secretSource: "none",
        supportsTextGeneration: true
      },
      {
        provider: "volcengine_tts",
        label: "火山豆包语音",
        configured: false,
        maskedSecret: "",
        baseUrl: "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        secretSource: "none",
        supportsTextGeneration: false
      }
    ]
  },
  aiProviderCatalog: [
    {
      provider: "openai",
      label: "OpenAI",
      kind: "commercial",
      region: "global",
      category: "model_hub",
      protocol: "openai_responses",
      modelSyncMode: "static",
      tags: ["文本", "视觉"],
      configured: true,
      baseUrl: "https://api.openai.com/v1/responses",
      secretSource: "secure_store",
      capabilities: ["text_generation", "vision", "speech_to_text"],
      requiresBaseUrl: false,
      supportsModelDiscovery: false,
      status: "ready"
    },
    {
      provider: "deepseek",
      label: "DeepSeek",
      kind: "commercial",
      region: "domestic",
      category: "text",
      protocol: "openai_chat",
      modelSyncMode: "remote",
      tags: ["国内", "文本"],
      configured: false,
      baseUrl: "https://api.deepseek.com/v1",
      secretSource: "none",
      capabilities: ["text_generation"],
      requiresBaseUrl: false,
      supportsModelDiscovery: true,
      status: "missing_secret"
    },
    {
      provider: "volcengine",
      label: "火山方舟",
      kind: "commercial",
      region: "domestic",
      category: "model_hub",
      protocol: "openai_chat",
      modelSyncMode: "remote",
      tags: ["国内", "文本", "视觉", "视频"],
      configured: false,
      baseUrl: "https://ark.cn-beijing.volces.com/api/v3",
      secretSource: "none",
      capabilities: ["text_generation", "vision", "asset_analysis", "video_generation"],
      requiresBaseUrl: false,
      supportsModelDiscovery: true,
      status: "missing_secret"
    },
    {
      provider: "volcengine_tts",
      label: "火山豆包语音",
      kind: "media",
      region: "domestic",
      category: "tts",
      protocol: "volcengine_tts",
      modelSyncMode: "manual",
      tags: ["国内", "豆包语音", "TTS"],
      configured: false,
      baseUrl: "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
      secretSource: "none",
      capabilities: ["tts"],
      requiresBaseUrl: false,
      supportsModelDiscovery: false,
      status: "missing_secret"
    }
  ],
  openAIModelCatalog: [
    {
      modelId: "gpt-5.4",
      displayName: "GPT-5.4",
      provider: "openai",
      capabilityTypes: ["text_generation", "vision"],
      inputModalities: ["text", "image"],
      outputModalities: ["text"],
      contextWindow: null,
      defaultFor: ["script_generation"],
      enabled: true
    },
    {
      modelId: "gpt-5",
      displayName: "GPT-5",
      provider: "openai",
      capabilityTypes: ["text_generation", "vision"],
      inputModalities: ["text", "image"],
      outputModalities: ["text"],
      contextWindow: null,
      defaultFor: ["script_generation"],
      enabled: true
    },
    {
      modelId: "gpt-5.4-mini",
      displayName: "GPT-5.4 Mini",
      provider: "openai",
      capabilityTypes: ["text_generation"],
      inputModalities: ["text"],
      outputModalities: ["text"],
      contextWindow: null,
      defaultFor: ["script_rewrite", "storyboard_generation"],
      enabled: true
    }
  ],
  aiCapabilitySupportMatrix: {
    capabilities: [
      {
        capabilityId: "script_generation",
        providers: ["openai", "deepseek", "volcengine"],
        models: [
          {
            provider: "openai",
            modelId: "gpt-5",
            displayName: "GPT-5",
            capabilityTypes: ["text_generation", "vision"]
          },
          {
            provider: "openai",
            modelId: "gpt-5.4",
            displayName: "GPT-5.4",
            capabilityTypes: ["text_generation", "vision"]
          },
          {
            provider: "deepseek",
            modelId: "deepseek-chat",
            displayName: "DeepSeek Chat",
            capabilityTypes: ["text_generation"]
          }
        ]
      }
    ]
  }
};

type RouteAwareFetchOptions = {
  fallbackUnhandledProviderHealth?: boolean;
};

function isUnhandledProviderHealthRequest(path: string, method: string, error: unknown): boolean {
  return (
    method === "GET" &&
    path === "/api/ai-providers/health" &&
    error instanceof Error &&
    error.message.startsWith("Unhandled request")
  );
}

export function createRouteAwareFetch(
  resolver: (path: string, method: string, init?: RequestInit) => unknown,
  options: RouteAwareFetchOptions = {}
) {
  const fallbackUnhandledProviderHealth = options.fallbackUnhandledProviderHealth ?? true;

  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const requestUrl = new URL(String(input));
    const path = `${requestUrl.pathname}${requestUrl.search}`;
    const method = (init?.method ?? "GET").toUpperCase();
    try {
      return resolver(path, method, init);
    } catch (error) {
      if (fallbackUnhandledProviderHealth && isUnhandledProviderHealthRequest(path, method, error)) {
        return okJsonResponse(runtimeFixtures.providerHealth);
      }
      throw error;
    }
  });
}

export async function mountApp(path: string) {
  const pinia = createPinia();
  const router = createAppRouter(pinia, createMemoryHistory());
  router.push(path);
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [pinia, router]
    }
  });

  return { wrapper, router, pinia };
}
