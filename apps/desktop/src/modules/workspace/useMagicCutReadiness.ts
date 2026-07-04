import { computed, type ComputedRef, type Ref } from "vue";

import { isModelAllowedBySupport } from "@/modules/settings/capabilityModelSupport";
import type {
  AICapabilitySettings,
  AICapabilitySupportMatrix,
  AIProviderCatalogItem
} from "@/types/runtime";

export type MagicCutReadiness = {
  available: boolean;
  message: string;
};

type MagicCutReadinessSources = {
  settings: Ref<AICapabilitySettings | null>;
  supportMatrix: Ref<AICapabilitySupportMatrix | null>;
  providerCatalog: Ref<AIProviderCatalogItem[]>;
  status: Ref<string>;
};

export function useMagicCutReadiness(
  sources: MagicCutReadinessSources
): ComputedRef<MagicCutReadiness> {
  return computed(() => {
    if (sources.status.value === "loading" && sources.settings.value === null) {
      return unavailable("正在同步 AI 能力配置。");
    }

    const settings = sources.settings.value;
    if (!settings) {
      return unavailable("AI 能力配置尚未同步，请刷新后重试。");
    }

    const capability = settings.capabilities.find((item) => item.capabilityId === "magic_cut");
    if (!capability) {
      return unavailable("未找到智能粗剪能力配置，请在 AI 与系统设置中重新保存配置。");
    }

    if (!capability.enabled) {
      return unavailable("智能粗剪能力未启用，请先在 AI 与系统设置中启用并保存。");
    }

    const providerSecret = settings.providers.find((item) => item.provider === capability.provider);
    const provider = sources.providerCatalog.value.find((item) => item.provider === capability.provider);
    if (!provider || !provider.capabilities.includes("text_generation")) {
      return unavailable("智能粗剪 Provider 未配置，请先选择可用文本模型。");
    }

    if (provider.configured === false || providerSecret?.configured === false) {
      return unavailable("智能粗剪 Provider 密钥缺失，请先完成密钥配置。");
    }

    const supportItem = sources.supportMatrix.value?.capabilities.find(
      (item) => item.capabilityId === "magic_cut"
    );
    const modelSupported = supportItem
      ? isModelAllowedBySupport(capability.provider, capability.model, supportItem.models)
      : true;
    if (supportItem && modelSupported === false) {
      return unavailable("当前模型不支持智能粗剪所需的文本生成能力，请更换模型。");
    }

    return {
      available: true,
      message: ""
    };
  });
}

function unavailable(reason: string): MagicCutReadiness {
  return {
    available: false,
    message: `智能粗剪暂不可用：${reason}`
  };
}
