import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { ref } from "vue";

import AICapabilityInspector from "@/modules/settings/components/AICapabilityInspector.vue";
import { capabilityLabel } from "@/pages/settings/ai-system-settings-page-helpers";
import { useMagicCutReadiness } from "@/modules/workspace/useMagicCutReadiness";
import { useCapabilityBinding } from "@/pages/settings/use-capability-binding";
import { usePromptEditing } from "@/pages/settings/use-prompt-editing";
import { useAIStore } from "@/stores/ai-capability";
import type { AICapabilitySettings } from "@/types/runtime";

const magicCutSettings = {
  scope: "runtime_local",
  configVersion: 1,
  diagnosticSummary: "测试能力矩阵",
  providers: [],
  capabilities: [
    {
      capabilityId: "magic_cut",
      enabled: true,
      provider: "openai",
      model: "gpt-5.4-mini",
      agentRole: "时间线剪辑 Agent",
      systemPrompt: "根据时间线上下文生成智能粗剪方案。",
      userPromptTemplate: "时间线上下文：{{timeline_context}}\n剪辑指令：{{instruction}}"
    }
  ]
} satisfies AICapabilitySettings;

describe("AI 设置 magic_cut 能力展示", () => {
  it("将 magic_cut 展示为智能粗剪，并提供时间线剪辑 Prompt 变量", () => {
    setActivePinia(createPinia());
    const aiStore = useAIStore();
    aiStore.settings = magicCutSettings;

    const { capabilityRows } = useCapabilityBinding();
    const { promptStates } = usePromptEditing(ref([]));

    expect(capabilityLabel("magic_cut")).toBe("智能粗剪");
    expect(capabilityRows.value[0]?.label).toBe("智能粗剪");
    expect(promptStates.value[0]).toMatchObject({
      capabilityId: "magic_cut",
      label: "智能粗剪",
      variables: ["timeline_context", "instruction"]
    });
  });

  it("智能粗剪 Provider 不支持文本生成时给出可恢复提示", () => {
    const readiness = useMagicCutReadiness({
      status: ref("ready"),
      settings: ref(magicCutSettings),
      supportMatrix: ref({
        capabilities: [
          {
            capabilityId: "magic_cut",
            providers: [],
            models: []
          }
        ]
      }),
      providerCatalog: ref([
        {
          provider: "openai",
          label: "OpenAI",
          kind: "hosted",
          region: "global",
          category: "video",
          protocol: "http",
          modelSyncMode: "static",
          tags: [],
          configured: true,
          baseUrl: "",
          secretSource: "secure_store",
          capabilities: ["video_generation"],
          requiresBaseUrl: false,
          supportsModelDiscovery: false,
          status: "ready"
        }
      ])
    });

    expect(readiness.value.available).toBe(false);
    expect(readiness.value.message).toBe(
      "智能粗剪暂不可用：智能粗剪 Provider 未配置，请先选择可用文本模型。"
    );
  });

  it("智能粗剪识别后端可解析的版本模型别名", () => {
    const settings = {
      ...magicCutSettings,
      capabilities: [
        {
          ...magicCutSettings.capabilities[0],
          model: "gpt-5.4"
        }
      ]
    };
    const readiness = useMagicCutReadiness({
      status: ref("ready"),
      settings: ref(settings),
      supportMatrix: ref({
        capabilities: [
          {
            capabilityId: "magic_cut",
            providers: ["openai"],
            models: [
              {
                provider: "openai",
                modelId: "gpt-5.4-20260501",
                displayName: "GPT-5.4 20260501",
                capabilityTypes: ["text_generation"]
              }
            ]
          }
        ]
      }),
      providerCatalog: ref([
        {
          provider: "openai",
          label: "OpenAI",
          kind: "hosted",
          region: "global",
          category: "model_hub",
          protocol: "openai_responses",
          modelSyncMode: "static",
          tags: [],
          configured: true,
          baseUrl: "",
          secretSource: "secure_store",
          capabilities: ["text_generation"],
          requiresBaseUrl: false,
          supportsModelDiscovery: false,
          status: "ready"
        }
      ])
    });

    expect(readiness.value.available).toBe(true);
  });

  it("智能粗剪 Inspector 不会把后端可解析的别名静默改成首个模型", async () => {
    const capability = {
      ...magicCutSettings.capabilities[0],
      provider: "openai",
      model: "gpt-5.4"
    };
    mount(AICapabilityInspector, {
      props: {
        capability,
        capabilityLabel: "智能粗剪",
        disabled: false,
        providerCatalog: [
          {
            provider: "openai",
            label: "OpenAI",
            kind: "hosted",
            region: "global",
            category: "model_hub",
            protocol: "openai_responses",
            modelSyncMode: "static",
            tags: [],
            configured: true,
            baseUrl: "",
            secretSource: "secure_store",
            capabilities: ["text_generation"],
            requiresBaseUrl: false,
            supportsModelDiscovery: false,
            status: "ready"
          }
        ],
        modelCatalogByProvider: {
          openai: [
            {
              provider: "openai",
              modelId: "gpt-5.4-20260501",
              displayName: "GPT-5.4 20260501",
              capabilityTypes: ["text_generation"],
              inputModalities: ["text"],
              outputModalities: ["text"],
              contextWindow: null,
              defaultFor: [],
              enabled: true
            }
          ]
        },
        supportItem: {
          capabilityId: "magic_cut",
          providers: ["openai"],
          models: [
            {
              provider: "openai",
              modelId: "gpt-5.4-20260501",
              displayName: "GPT-5.4 20260501",
              capabilityTypes: ["text_generation"]
            }
          ]
        }
      }
    });

    await Promise.resolve();

    expect(capability.model).toBe("gpt-5.4");
  });

  it("智能粗剪模型下拉只展示支持矩阵允许的文本模型", () => {
    const capability = {
      ...magicCutSettings.capabilities[0],
      provider: "openai",
      model: "seedance-video"
    };
    const wrapper = mount(AICapabilityInspector, {
      props: {
        capability,
        capabilityLabel: "智能粗剪",
        disabled: false,
        providerCatalog: [
          {
            provider: "openai",
            label: "OpenAI",
            kind: "hosted",
            region: "global",
            category: "model_hub",
            protocol: "openai_responses",
            modelSyncMode: "static",
            tags: [],
            configured: true,
            baseUrl: "",
            secretSource: "secure_store",
            capabilities: ["text_generation"],
            requiresBaseUrl: false,
            supportsModelDiscovery: false,
            status: "ready"
          }
        ],
        modelCatalogByProvider: {
          openai: [
            {
              provider: "openai",
              modelId: "gpt-5.4-mini",
              displayName: "GPT-5.4 Mini",
              capabilityTypes: ["text_generation"],
              inputModalities: ["text"],
              outputModalities: ["text"],
              contextWindow: null,
              defaultFor: [],
              enabled: true
            },
            {
              provider: "openai",
              modelId: "seedance-video",
              displayName: "Seedance Video",
              capabilityTypes: ["video_generation"],
              inputModalities: ["text"],
              outputModalities: ["video"],
              contextWindow: null,
              defaultFor: ["magic_cut"],
              enabled: true
            }
          ]
        },
        supportItem: {
          capabilityId: "magic_cut",
          providers: ["openai"],
          models: [
            {
              provider: "openai",
              modelId: "gpt-5.4-mini",
              displayName: "GPT-5.4 Mini",
              capabilityTypes: ["text_generation"]
            }
          ]
        }
      }
    });

    const modelOptions = wrapper
      .get('select[data-field="capability.magic_cut.model"]')
      .findAll("option")
      .map((item) => item.text());

    expect(modelOptions).toContain("GPT-5.4 Mini");
    expect(modelOptions).not.toContain("Seedance Video");
  });
});
