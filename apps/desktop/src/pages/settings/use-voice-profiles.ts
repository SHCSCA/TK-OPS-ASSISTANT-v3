import { computed, onMounted, ref } from "vue";
import { useAICapabilityStore } from "@/stores/ai-capability";
import { fetchVoiceProfiles } from "@/app/runtime-client";
import type { VoiceProfileDto } from "@/types/runtime";

/**
 * 音色管理：TTS Provider 筛选、音色选择与试听
 * 设置页面使用独立的音色列表（不依赖 voice-studio store 的项目上下文）
 */
export function useVoiceProfiles() {
  const aiStore = useAICapabilityStore();

  const allProfiles = ref<VoiceProfileDto[]>([]);
  const selectedTtsProviderId = ref("openai");
  const selectedVoiceId = ref("");
  const previewingVoiceId = ref<string | null>(null);

  /** 仅筛选支持 TTS 能力的 Provider */
  const ttsProviders = computed(() =>
    aiStore.providerCatalog.filter(p => p.capabilities.includes("tts"))
  );

  /** 按当前 TTS Provider 过滤音色 */
  const voiceProfiles = computed(() =>
    allProfiles.value.filter(v => v.provider === selectedTtsProviderId.value)
  );

  async function loadProfiles() {
    try {
      allProfiles.value = await fetchVoiceProfiles();
    } catch {
      // 音色加载失败不阻塞页面
      allProfiles.value = [];
    }
  }

  async function previewVoice(id: string) {
    previewingVoiceId.value = id;
    // 实际应调用 TTS 生成接口播放试听音频，当前用定时器模拟
    setTimeout(() => { previewingVoiceId.value = null; }, 3000);
  }

  onMounted(() => { void loadProfiles(); });

  return {
    selectedTtsProviderId,
    selectedVoiceId,
    previewingVoiceId,
    ttsProviders,
    voiceProfiles,
    previewVoice,
    loadProfiles
  };
}
