import { ref, watch } from "vue";
import { useAIStore } from "@/stores/ai-capability";
import type { CapabilityBindingRow, PromptEditorState } from "./types";

/** 每项能力可用的模板变量 */
const PROMPT_VARIABLES: Record<string, string[]> = {
  script_generation: ["topic", "instructions"],
  script_rewrite: ["script", "instructions"],
  storyboard_generation: ["script"],
  tts_generation: ["text", "voice_id"],
  subtitle_alignment: ["text", "audio_url"],
  video_transcription: ["media_file"]
};

/** 能力 ID → 中文标签 */
const CAPABILITY_LABELS: Record<string, string> = {
  script_generation: "脚本生成",
  script_rewrite: "脚本改写",
  storyboard_generation: "分镜生成",
  tts_generation: "配音生成",
  subtitle_alignment: "字幕对齐",
  video_transcription: "视频解析",
  video_generation: "视频生成",
  asset_analysis: "素材/视频分析"
};

/**
 * Prompt 模板编辑：角色设定、系统 Prompt、用户模板管理
 */
export function usePromptEditing(capabilityRows: ReturnType<typeof ref<CapabilityBindingRow[]>>) {
  const aiStore = useAIStore();

  const promptStates = ref<PromptEditorState[]>([]);

  watch(() => aiStore.settings?.capabilities, (val) => {
    if (val) {
      promptStates.value = val.map(c => ({
        capabilityId: c.capabilityId,
        label: CAPABILITY_LABELS[c.capabilityId] || c.capabilityId,
        agentRole: c.agentRole,
        systemPrompt: c.systemPrompt,
        userPromptTemplate: c.userPromptTemplate,
        variables: PROMPT_VARIABLES[c.capabilityId] || ["content"],
        expanded: false
      }));
    }
  }, { immediate: true });

  function togglePrompt(id: string) {
    promptStates.value.forEach(p => {
      p.expanded = p.capabilityId === id ? !p.expanded : false;
    });
  }

  function updatePrompt(patch: Partial<PromptEditorState> & { capabilityId: string }) {
    const index = promptStates.value.findIndex(p => p.capabilityId === patch.capabilityId);
    if (index !== -1) {
      promptStates.value[index] = { ...promptStates.value[index], ...patch };
    }
  }

  async function savePrompt(id: string) {
    const p = promptStates.value.find(item => item.capabilityId === id);
    if (!p || !capabilityRows.value) return;
    
    const updatedCapabilities = capabilityRows.value.map(r => {
      if (r.capabilityId === id) {
        return { ...r, agentRole: p.agentRole, systemPrompt: p.systemPrompt, userPromptTemplate: p.userPromptTemplate };
      }
      return r;
    });

    // FIX: Match the required Partial<AICapabilitySettings> contract
    await aiStore.saveCapabilities({ 
      capabilities: updatedCapabilities 
    });
  }

  function resetPrompt(id: string) {
    const orig = aiStore.settings?.capabilities.find(c => c.capabilityId === id);
    if (orig) {
      updatePrompt({
        capabilityId: id,
        agentRole: orig.agentRole,
        systemPrompt: orig.systemPrompt,
        userPromptTemplate: orig.userPromptTemplate
      });
    }
  }

  return {
    promptStates,
    togglePrompt,
    updatePrompt,
    savePrompt,
    resetPrompt
  };
}
