<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">配音参数</span>
        <strong>速度 / 音调 / 情绪</strong>
      </div>
      <span class="panel-heading__chip" :data-state="locked ? 'disabled' : 'ready'">
        {{ locked ? "锁定" : "可编辑" }}
      </span>
    </header>

    <div v-if="locked" class="state-surface state-surface--locked">
      <strong>参数面板已锁定。</strong>
      <p>{{ lockedReason }}</p>
    </div>

    <fieldset class="params-fieldset" :disabled="locked">
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
    </fieldset>
  </section>
</template>

<script setup lang="ts">
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
  { id: "calm", label: "平静" },
  { id: "happy", label: "欢快" },
  { id: "news", label: "播报" },
  { id: "tender", label: "温柔" }
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
  display: grid;
  gap: 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-heading > div {
  display: grid;
  gap: 4px;
}

.panel-heading__kicker {
  color: var(--text-tertiary);
  font-size: 12px;
}

.panel-heading strong {
  color: var(--text-primary);
  font-size: 14px;
}

.panel-heading__chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.panel-heading__chip[data-state="disabled"] {
  border-color: color-mix(in srgb, var(--warning) 30%, transparent);
  color: var(--warning);
}

.panel-heading__chip[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 30%, transparent);
  color: var(--brand-primary);
}

.state-surface {
  display: grid;
  gap: 6px;
  margin: 0 16px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.state-surface--locked {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
}

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.params-fieldset {
  display: grid;
  gap: 14px;
  border: 0;
  padding: 0 16px 16px;
  margin: 0;
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
  gap: 8px;
}

.emotion-button {
  min-height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition:
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.emotion-button:hover,
.emotion-button--active {
  border-color: color-mix(in srgb, var(--brand-primary) 40%, transparent);
  color: var(--brand-primary);
}

.emotion-button:hover {
  transform: translateY(-1px);
}

.params-fieldset:disabled .emotion-button {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  .emotion-button {
    transition: none;
  }

  .emotion-button:hover {
    transform: none;
  }
}
</style>
