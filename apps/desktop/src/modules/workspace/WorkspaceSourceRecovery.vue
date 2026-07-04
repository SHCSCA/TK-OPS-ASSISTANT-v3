<template>
  <section
    class="workspace-source-recovery"
    data-testid="workspace-source-recovery"
    aria-live="polite"
  >
    <div class="workspace-source-recovery__icon" aria-hidden="true">
      <span class="material-symbols-outlined">rule_folder</span>
    </div>
    <div class="workspace-source-recovery__body">
      <div class="workspace-source-recovery__heading">
        <strong>{{ heading }}</strong>
        <span>{{ statusLabel }}</span>
      </div>
      <p>{{ message }}</p>
      <ul class="workspace-source-recovery__list" aria-label="缺少或未就绪的来源">
        <li v-for="source in sources" :key="source.kind">
          <strong>{{ source.label }}</strong>
          <span>{{ source.message }}</span>
        </li>
      </ul>
      <p class="workspace-source-recovery__next-step">{{ nextStep }}</p>
    </div>
    <div class="workspace-source-recovery__actions" aria-label="恢复动作">
      <button
        v-if="showVoiceAction"
        type="button"
        data-testid="workspace-source-recovery-voice-button"
        @click="$emit('openVoiceStudio')"
      >
        <span class="material-symbols-outlined">record_voice_over</span>
        去配音中心
      </button>
      <button
        v-if="showTtsSettingsAction"
        type="button"
        data-testid="workspace-source-recovery-settings-button"
        @click="$emit('openTtsSettings')"
      >
        <span class="material-symbols-outlined">settings_suggest</span>
        打开 AI 设置
      </button>
      <button
        type="button"
        data-testid="workspace-source-recovery-precheck-button"
        :disabled="disabled"
        @click="$emit('precheck')"
      >
        <span class="material-symbols-outlined">rule_settings</span>
        本地预检
      </button>
      <button
        type="button"
        data-testid="workspace-source-recovery-assemble-button"
        :disabled="disabled"
        @click="$emit('sync')"
      >
        <span class="material-symbols-outlined">sync</span>
        重新同步 AI 三轨
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  disabled: boolean;
  heading: string;
  message: string;
  nextStep: string;
  showTtsSettingsAction: boolean;
  showVoiceAction: boolean;
  sources: Array<{ kind: string; label: string; message: string }>;
  statusLabel: string;
}>();

defineEmits<{
  openTtsSettings: [];
  openVoiceStudio: [];
  precheck: [];
  sync: [];
}>();
</script>

<style scoped>
.workspace-source-recovery {
  align-items: start;
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--color-warning) 13%, var(--color-bg-surface)),
      var(--color-bg-surface)
    );
  border: 1px solid color-mix(in srgb, var(--color-warning) 36%, var(--color-border-default));
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: var(--space-3) var(--space-4);
}

.workspace-source-recovery__icon {
  align-items: center;
  background: color-mix(in srgb, var(--color-warning) 16%, var(--color-bg-muted));
  border: 1px solid color-mix(in srgb, var(--color-warning) 30%, var(--color-border-default));
  border-radius: var(--radius-md);
  color: var(--color-warning);
  display: grid;
  height: 38px;
  place-items: center;
  width: 38px;
}

.workspace-source-recovery__body {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.workspace-source-recovery__heading {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: space-between;
}

.workspace-source-recovery__heading strong {
  font: var(--font-title-sm);
}

.workspace-source-recovery__heading span {
  background: color-mix(in srgb, var(--color-warning) 16%, var(--color-bg-muted));
  border: 1px solid color-mix(in srgb, var(--color-warning) 28%, var(--color-border-default));
  border-radius: 999px;
  color: var(--color-text-secondary);
  font: var(--font-label-sm);
  padding: 3px 8px;
}

.workspace-source-recovery p {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  margin: 0;
}

.workspace-source-recovery__list {
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  list-style: none;
  margin: 0;
  padding: 0;
}

.workspace-source-recovery__list li {
  background: color-mix(in srgb, var(--color-bg-muted) 78%, transparent);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  display: grid;
  gap: 3px;
  min-width: 0;
  padding: 8px 10px;
}

.workspace-source-recovery__list strong {
  font: var(--font-label-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-source-recovery__list span {
  color: var(--color-text-secondary);
  font: var(--font-caption);
  line-height: 1.45;
}

.workspace-source-recovery .workspace-source-recovery__next-step {
  color: var(--color-text-primary);
}

.workspace-source-recovery__actions {
  align-items: stretch;
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(2, minmax(132px, 1fr));
  min-width: min(100%, 328px);
}

.workspace-source-recovery__actions button {
  align-items: center;
  background: var(--color-brand-primary);
  border: 1px solid var(--color-brand-primary);
  border-radius: var(--radius-md);
  color: var(--color-text-on-brand);
  cursor: pointer;
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-2);
  justify-content: center;
  min-height: 34px;
  padding: 0 var(--space-3);
  text-align: center;
}

.workspace-source-recovery__actions button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

@container editing-workspace (max-width: 860px) {
  .workspace-source-recovery {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .workspace-source-recovery__actions {
    grid-column: 1 / -1;
    min-width: 0;
  }

  .workspace-source-recovery__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container editing-workspace (max-width: 620px) {
  .workspace-source-recovery__actions,
  .workspace-source-recovery__list {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
