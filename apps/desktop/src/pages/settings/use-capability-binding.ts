import { ref, watch } from "vue";
import { useAIStore } from "@/stores/ai-capability";
import type { CapabilityBindingRow } from "./types";

/** 能力 ID → 中文标签 */
const CAPABILITY_LABELS: Record<string, string> = {
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  tts_generation: "配音生成",
  subtitle_alignment: "字幕对齐",
  video_generation: "视频生成",
  asset_analysis: "素材分析"
};

/**
 * 能力绑定矩阵：7 项 AI 能力的 Provider/Model 绑定管理
 */
export function useCapabilityBinding() {
  const aiStore = useAIStore();

  const capabilityRows = ref<CapabilityBindingRow[]>([]);
  const capabilityDirty = ref(false);

  watch(() => aiStore.settings?.capabilities, (val) => {
    if (val) {
      capabilityRows.value = val.map(c => ({
        ...c,
        label: CAPABILITY_LABELS[c.capabilityId] || c.capabilityId,
        status: "ready"
      }));
      capabilityDirty.value = false;
    }
  }, { immediate: true });

  function updateCapabilityRow(patch: Partial<CapabilityBindingRow> & { capabilityId: string }) {
    const index = capabilityRows.value.findIndex(r => r.capabilityId === patch.capabilityId);
    if (index !== -1) {
      capabilityRows.value[index] = { ...capabilityRows.value[index], ...patch };
      capabilityDirty.value = true;
    }
  }

  async function saveCapabilities() {
    // FIX: Match the required Partial<AICapabilitySettings> contract
    await aiStore.saveCapabilities({ 
      capabilities: capabilityRows.value 
    });
    capabilityDirty.value = false;
  }

  function resetCapabilities() {
    if (aiStore.settings) {
      capabilityRows.value = aiStore.settings.capabilities.map(c => ({
        ...c,
        label: CAPABILITY_LABELS[c.capabilityId] || c.capabilityId,
        status: "ready"
      }));
      capabilityDirty.value = false;
    }
  }

  return {
    capabilityRows,
    capabilityDirty,
    capabilityLabels: CAPABILITY_LABELS,
    updateCapabilityRow,
    saveCapabilities,
    resetCapabilities
  };
}
