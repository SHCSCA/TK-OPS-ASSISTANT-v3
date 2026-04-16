<template>
  <section class="voice-params-panel">
    <header class="panel-heading">配音参数</header>

    <label class="field-row">
      <span>语速 {{ config.speed.toFixed(1) }}x</span>
      <input
        :value="config.speed"
        max="2"
        min="0.5"
        step="0.1"
        type="range"
        @input="updateConfig({ speed: Number(($event.target as HTMLInputElement).value) })"
      />
    </label>

    <label class="field-row">
      <span>音调 {{ config.pitch > 0 ? "+" : "" }}{{ config.pitch }}</span>
      <input
        :value="config.pitch"
        max="50"
        min="-50"
        step="1"
        type="range"
        @input="updateConfig({ pitch: Number(($event.target as HTMLInputElement).value) })"
      />
    </label>

    <div class="field-row">
      <span>情绪</span>
      <div class="emotion-list">
        <button
          v-for="emotion in emotions"
          :key="emotion.id"
          class="emotion-button"
          :class="{ 'emotion-button--active': config.emotion === emotion.id }"
          type="button"
          @click="updateConfig({ emotion: emotion.id })"
        >
          {{ emotion.label }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { VoiceConfig } from "@/stores/voice-studio";

const props = defineProps<{
  config: VoiceConfig;
}>();

const emit = defineEmits<{
  "update:config": [config: VoiceConfig];
}>();

const emotions = [
  { id: "calm", label: "平静" },
  { id: "happy", label: "欢快" },
  { id: "news", label: "播报" },
  { id: "tender", label: "温柔" }
];

function updateConfig(patch: Partial<VoiceConfig>) {
  emit("update:config", {
    ...props.config,
    ...patch
  });
}
</script>

<style scoped>
.voice-params-panel {
  display: grid;
  gap: 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  padding: 14px;
}

.panel-heading {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.field-row {
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.field-row input[type="range"] {
  width: 100%;
  accent-color: var(--brand-primary);
}

.emotion-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.emotion-button {
  min-height: 32px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
}

.emotion-button--active,
.emotion-button:hover {
  border-color: var(--brand-primary);
  color: var(--brand-primary);
}
</style>
