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
    machineId: "machine-001",
    machineBound: true,
    activationMode: "placeholder",
    maskedCode: "TK-O****************0001",
    activatedAt: "2026-04-11T10:00:00Z"
  },
  restrictedLicense: {
    active: false,
    restrictedMode: true,
    machineId: "machine-001",
    machineBound: false,
    activationMode: "placeholder",
    maskedCode: "",
    activatedAt: null
  },
  health: {
    service: "online",
    version: "0.1.1",
    now: "2026-04-11T10:00:00Z",
    mode: "development"
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
      voice: "alloy",
      subtitleMode: "balanced"
    }
  },
  diagnostics: {
    databasePath: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/runtime.db",
    logDir: "G:/AI/TK-OPS-ASSISTANT-V3/.runtime-data/logs",
    revision: 1,
    mode: "development",
    healthStatus: "online"
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
        provider: "openai",
        model: "gpt-5-mini",
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
        capabilityId: "video_generation",
        enabled: false,
        provider: "openai",
        model: "gpt-5-mini",
        agentRole: "视频生成导演",
        systemPrompt: "把分镜转成可执行的视频生成提示。",
        userPromptTemplate: "分镜内容：\\n{{storyboard}}"
      },
      {
        capabilityId: "asset_analysis",
        enabled: false,
        provider: "openai",
        model: "gpt-5-mini",
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
        provider: "openai_compatible",
        label: "OpenAI-compatible",
        configured: false,
        maskedSecret: "",
        baseUrl: "",
        secretSource: "none",
        supportsTextGeneration: true
      },
      {
        provider: "anthropic",
        label: "Anthropic",
        configured: false,
        maskedSecret: "",
        baseUrl: "https://api.anthropic.com/v1/messages",
        secretSource: "none",
        supportsTextGeneration: false
      },
      {
        provider: "gemini",
        label: "Gemini",
        configured: false,
        maskedSecret: "",
        baseUrl: "https://generativelanguage.googleapis.com/v1beta/models",
        secretSource: "none",
        supportsTextGeneration: false
      }
    ]
  }
};

export function createRouteAwareFetch(
  resolver: (path: string, method: string, init?: RequestInit) => unknown
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const requestUrl = new URL(String(input));
    const path = `${requestUrl.pathname}${requestUrl.search}`;
    const method = (init?.method ?? "GET").toUpperCase();
    return resolver(path, method, init);
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
