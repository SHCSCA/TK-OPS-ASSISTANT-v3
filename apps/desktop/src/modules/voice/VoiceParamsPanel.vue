<template>
  <section class="panel-shell flex flex-col">
    <header class="panel-heading">
      <div class="panel-heading__title">
        <span class="panel-heading__kicker">配音参数</span>
        <strong>速度 / 音调 / 情绪</strong>
      </div>
      <span class="panel-heading__chip" :data-state="locked ? 'disabled' : 'ready'">
        {{ locked ? "锁定" : "可编辑" }}
      </span>
    </header>

    <div v-if="locked" class="state-surface state-surface--locked">
      <span class="material-symbols-outlined text-warning">lock</span>
      <strong>参数面板已锁定</strong>
      <p>{{ lockedReason }}</p>
    </div>

    <fieldset class="params-fieldset custom-scrollbar" :disabled="locked">
      <div class="field-group">
        <div class="field-header">
          <span class="field-label">语速</span>
          <span class="field-value">{{ config.speed.toFixed(1) }}x</span>
        </div>
        <div class="slider-container">
          <input
            :value="config.speed"
            max="2"
            min="0.5"
            step="0.1"
            type="range"
            class="param-slider"
            @input="updateConfig({ speed: Number(($event.target as HTMLInputElement).value) })"
          />
          <div class="slider-marks">
            <span>0.5</span>
            <span>1.0</span>
            <span>2.0</span>
          </div>
        </div>
      </div>

      <div class="field-group">
        <div class="field-header">
          <span class="field-label">音调</span>
          <span class="field-value">{{ config.pitch > 0 ? "+" : "" }}{{ config.pitch }}</span>
        </div>
        <div class="slider-container">
          <input
            :value="config.pitch"
            max="50"
            min="-50"
            step="1"
            type="range"
            class="param-slider"
            @input="updateConfig({ pitch: Number(($event.target as HTMLInputElement).value) })"
          />
          <div class="slider-marks">
            <span>-50</span>
            <span>0</span>
            <span>+50</span>
          </div>
        </div>
      </div>

      <div class="field-group">
        <div class="field-header">
          <span class="field-label">预设情绪</span>
        </div>
        <div class="emotion-grid">
          <button
            v-for="emotion in emotions"
            :key="emotion.id"
            class="emotion-card"
            :class="{ 'emotion-card--active': config.emotion === emotion.id }"
            type="button"
            @click="updateConfig({ emotion: emotion.id })"
          >
            <span class="material-symbols-outlined">{{ emotion.icon }}</span>
            <span class="emotion-label">{{ emotion.label }}</span>
          </button>
        </div>
      </div>
    </fieldset>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { VoiceConfig } from "@/stores/voice-studio";

const props = defineProps<{
  config: VoiceConfig;
  locked: boolean;
  lockedReason: string;
}>();

const emit = defineEmits<{
  "update:config": [config: VoiceConfig];
}>();

const emotions = [
  { id: "calm", label: "平静", icon: "sentiment_satisfied" },
  { id: "happy", label: "欢快", icon: "mood" },
  { id: "news", label: "播报", icon: "record_voice_over" },
  { id: "tender", label: "温柔", icon: "favorite" }
];

function updateConfig(patch: Partial<VoiceConfig>): void {
  emit("update:config", {
    ...props.config,
    ...patch
  });
}
</script>

<style scoped>
.panel-shell {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
}

.panel-heading__title {
  display: grid;
  gap: 2px;
}

.panel-heading__kicker {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
  text-transform: uppercase;
  letter-spacing: var(--ls-caption);
}

.panel-heading strong {
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.panel-heading__chip {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font: var(--font-caption);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-default);
}

.panel-heading__chip[data-state="disabled"] {
  color: var(--color-warning);
  border-color: rgba(245, 183, 64, 0.4);
}

.panel-heading__chip[data-state="ready"] {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-secondary);
}

.state-surface {
  margin: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-muted);
  text-align: center;
  display: grid;
  gap: 4px;
}

.state-surface .material-symbols-outlined {
  font-size: 24px;
  margin-bottom: 4px;
}

.state-surface strong {
  font: var(--font-title-sm);
}

.state-surface p {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.params-fieldset {
  display: grid;
  gap: var(--space-6);
  border: 0;
  padding: var(--space-5) var(--space-4);
  margin: 0;
  overflow-y: auto;
}

.field-group {
  display: grid;
  gap: var(--space-3);
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  font: var(--font-body-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.field-value {
  font: var(--font-caption);
  font-family: var(--font-code);
  color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.slider-container {
  display: grid;
  gap: 4px;
}

.param-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: var(--color-border-default);
  border-radius: var(--radius-full);
  outline: none;
  accent-color: var(--color-brand-primary);
}

.slider-marks {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
}

.slider-marks span {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.emotion-grid {
  display: grid;
  /* 窄面板自动降为单列，宽面板保持双列 */
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: var(--space-2);
  min-width: 0;
}

.emotion-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: var(--space-3);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.emotion-card:hover {
  border-color: var(--color-brand-secondary);
  background: var(--color-bg-muted);
}

.emotion-card--active {
  border-color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.04);
  color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary);
}

.emotion-card .material-symbols-outlined {
  font-size: 20px;
}

.emotion-label {
  font: var(--font-caption);
  font-weight: 600;
}

.params-fieldset:disabled {
  opacity: 0.6;
  pointer-events: none;
}
</style>
