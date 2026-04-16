<template>
  <section class="voice-preview-stage" data-testid="voice-preview-stage">
    <div class="stage-kicker">声音导演台</div>
    <h2>{{ title }}</h2>
    <p class="stage-copy">{{ activeParagraphText }}</p>

    <div class="wave-stage" :class="{ 'wave-stage--busy': status === 'generating' }">
      <span
        v-for="bar in bars"
        :key="bar.index"
        class="wave-bar"
        :style="{ height: `${bar.height}px` }"
      />
    </div>

    <div class="stage-status" :class="`stage-status--${status}`">
      <strong>{{ statusLabel }}</strong>
      <span>{{ statusMessage }}</span>
    </div>

    <audio
      v-if="selectedTrack?.filePath"
      class="audio-preview"
      controls
      :src="selectedTrack.filePath"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";
import type { VoiceTrackDto } from "@/types/runtime";

const props = defineProps<{
  activeParagraph: Paragraph | null;
  generationMessage: string | null;
  selectedTrack: VoiceTrackDto | null;
  status: VoiceStudioStatus;
}>();

const bars = Array.from({ length: 36 }, (_, index) => ({
  height: 14 + Math.round(Math.abs(Math.sin(index * 0.78) * 42)),
  index
}));

const title = computed(() => {
  if (props.status === "generating") return "正在创建配音版本";
  if (props.status === "blocked") return "待配置 AI Provider";
  return "组织脚本声线与节奏";
});

const activeParagraphText = computed(() => {
  return props.activeParagraph?.text ?? "选择脚本段落后，这里会展示当前配音上下文。";
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "generating") return "生成中";
  if (props.status === "blocked") return "待配置 AI Provider";
  if (props.status === "error") return "需要处理";
  return "准备就绪";
});

const statusMessage = computed(() => {
  if (props.generationMessage) return props.generationMessage;
  if (props.status === "generating") return "正在把脚本段落整理为配音版本记录。";
  if (props.status === "blocked") return "尚未配置可用 TTS Provider，配音版本已作为草稿保存。";
  if (props.status === "error") return "请根据页面提示修正后重试。";
  return "选择音色和参数后，可生成真实 Runtime 配音版本记录。";
});
</script>

<style scoped>
.voice-preview-stage {
  display: grid;
  align-content: center;
  gap: 18px;
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 10%, transparent), transparent 42%),
    var(--bg-elevated);
  padding: 24px;
  overflow: hidden;
}

.stage-kicker {
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 28px;
  line-height: 1.2;
}

.stage-copy {
  max-width: 760px;
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.75;
}

.wave-stage {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 112px;
  padding: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: color-mix(in srgb, var(--bg-base) 80%, transparent);
}

.wave-bar {
  width: 7px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--brand-primary) 78%, var(--text-primary));
  opacity: 0.72;
}

.wave-stage--busy .wave-bar {
  animation: voice-pulse 1.1s ease-in-out infinite alternate;
}

.wave-stage--busy .wave-bar:nth-child(2n) {
  animation-delay: 120ms;
}

.wave-stage--busy .wave-bar:nth-child(3n) {
  animation-delay: 220ms;
}

.stage-status {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
}

.stage-status strong {
  color: var(--text-primary);
}

.stage-status--blocked strong {
  color: var(--warning, #b7791f);
}

.stage-status--error strong {
  color: var(--danger, #dc2626);
}

.audio-preview {
  width: 100%;
}

@keyframes voice-pulse {
  from {
    opacity: 0.46;
    transform: scaleY(0.72);
  }
  to {
    opacity: 0.96;
    transform: scaleY(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wave-stage--busy .wave-bar {
    animation: none;
  }
}
</style>
