<template>
  <div class="bootstrap-overlay" :data-bootstrap-overlay="mode">
    <div class="bootstrap-overlay__panel">
      <p class="bootstrap-overlay__eyebrow">TK-OPS 启动准备</p>
      <h2>{{ title }}</h2>
      <p class="bootstrap-overlay__summary">{{ summary }}</p>

      <ol class="bootstrap-overlay__steps">
        <li
          v-for="step in steps"
          :key="step.id"
          class="bootstrap-overlay__step"
          :class="`bootstrap-overlay__step--${step.status}`"
        >
          <span class="bootstrap-overlay__dot" />
          <span>{{ step.label }}</span>
        </li>
      </ol>

      <div v-if="mode === 'error'" class="bootstrap-overlay__error">
        <p>{{ errorSummary }}</p>
        <button class="settings-page__button" type="button" data-action="retry-bootstrap" @click="$emit('retry')">
          重新检查
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export type BootstrapStep = {
  id: string;
  label: string;
  status: "pending" | "loading" | "ready" | "error";
};

defineEmits<{
  retry: [];
}>();

defineProps<{
  errorSummary: string;
  mode: "loading" | "error";
  steps: BootstrapStep[];
  summary: string;
  title: string;
}>();
</script>

<style scoped>
.bootstrap-overlay {
  align-items: center;
  background: color-mix(in srgb, var(--surface-primary) 90%, rgba(15, 23, 42, 0.1));
  display: grid;
  inset: 0;
  justify-items: center;
  padding: var(--space-6);
  position: fixed;
  z-index: 40;
}

.bootstrap-overlay__panel {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  display: grid;
  gap: var(--space-4);
  max-width: 560px;
  padding: 32px;
  width: min(100%, 560px);
}

.bootstrap-overlay__eyebrow {
  color: var(--text-secondary);
  font-size: 12px;
  letter-spacing: 0.08em;
  margin: 0;
  text-transform: uppercase;
}

.bootstrap-overlay__panel h2,
.bootstrap-overlay__summary,
.bootstrap-overlay__steps,
.bootstrap-overlay__error p {
  margin: 0;
}

.bootstrap-overlay__summary,
.bootstrap-overlay__error p {
  color: var(--text-secondary);
}

.bootstrap-overlay__steps {
  display: grid;
  gap: var(--space-3);
  list-style: none;
  padding: 0;
}

.bootstrap-overlay__step {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  display: flex;
  gap: var(--space-3);
  padding: 12px 14px;
}

.bootstrap-overlay__dot {
  border-radius: 999px;
  display: inline-flex;
  height: 10px;
  width: 10px;
}

.bootstrap-overlay__step--pending .bootstrap-overlay__dot {
  background: var(--text-tertiary);
}

.bootstrap-overlay__step--loading .bootstrap-overlay__dot {
  background: var(--status-warning);
}

.bootstrap-overlay__step--ready .bootstrap-overlay__dot {
  background: var(--status-success);
}

.bootstrap-overlay__step--error .bootstrap-overlay__dot {
  background: var(--status-error);
}

.bootstrap-overlay__error {
  display: grid;
  gap: var(--space-3);
}
</style>
