<template>
  <section
    v-if="feedback"
    class="workspace-command-feedback"
    :data-tone="feedback.tone"
    data-testid="workspace-command-feedback"
    role="status"
    aria-live="polite"
  >
    <div class="workspace-command-feedback__icon" :data-status="feedback.status">
      <span class="material-symbols-outlined" :class="{ spinning: feedback.spinning }">
        {{ feedback.icon }}
      </span>
    </div>

    <div class="workspace-command-feedback__body">
      <div class="workspace-command-feedback__header">
        <strong>{{ feedback.title }}</strong>
        <span>{{ feedback.detail }}</span>
      </div>

      <div
        v-if="feedback.showProgress"
        class="workspace-command-feedback__progress"
        data-testid="workspace-command-progress"
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-valuenow="String(feedback.progress)"
      >
        <span :style="{ width: `${feedback.progress}%` }" />
      </div>
    </div>

    <div class="workspace-command-feedback__actions">
      <button
        v-if="feedback.canCancel"
        class="workspace-command-feedback__button"
        data-testid="workspace-command-cancel-button"
        type="button"
        :disabled="cancelPending"
        @click="emit('cancel', feedback.taskId)"
      >
        <span class="material-symbols-outlined">stop_circle</span>
        {{ cancelPending ? "正在取消" : "取消任务" }}
      </button>
      <button
        v-if="feedback.canRetry"
        class="workspace-command-feedback__button workspace-command-feedback__button--primary"
        data-testid="workspace-command-retry-button"
        type="button"
        :disabled="retryDisabled"
        @click="emit('retry')"
      >
        <span class="material-symbols-outlined">replay</span>
        重新智能粗剪
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { buildWorkspaceCommandFeedback } from "@/modules/workspace/workspaceCommandFeedback";
import type { TaskInfo } from "@/types/task-events";
import type { WorkspaceAICommandResultDto } from "@/types/runtime";

const props = withDefaults(
  defineProps<{
    activeTask: TaskInfo | null;
    cancelPending?: boolean;
    lastCommandResult: WorkspaceAICommandResultDto | null;
    retryDisabled?: boolean;
  }>(),
  {
    cancelPending: false,
    retryDisabled: false
  }
);

const emit = defineEmits<{
  cancel: [taskId: string];
  retry: [];
}>();

const feedback = computed(() => buildWorkspaceCommandFeedback(props.activeTask, props.lastCommandResult));
</script>

<style scoped>
.workspace-command-feedback {
  align-items: center;
  background: color-mix(in srgb, var(--color-bg-surface) 92%, var(--color-brand-primary));
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  display: flex;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-3);
}

.workspace-command-feedback[data-tone="danger"] {
  background: color-mix(in srgb, var(--color-danger-surface, var(--color-bg-surface)) 80%, var(--color-bg-surface));
  border-color: color-mix(in srgb, var(--color-danger, #ef4444) 42%, var(--color-border-default));
}

.workspace-command-feedback[data-tone="success"] {
  border-color: color-mix(in srgb, var(--color-success, #10b981) 38%, var(--color-border-default));
}

.workspace-command-feedback[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning, #f59e0b) 42%, var(--color-border-default));
}

.workspace-command-feedback__icon {
  align-items: center;
  background: color-mix(in srgb, var(--color-brand-primary) 14%, transparent);
  border-radius: 999px;
  color: var(--color-brand-primary);
  display: inline-flex;
  flex: 0 0 auto;
  height: 34px;
  justify-content: center;
  width: 34px;
}

.workspace-command-feedback__icon[data-status="failed"] {
  background: color-mix(in srgb, var(--color-danger, #ef4444) 14%, transparent);
  color: var(--color-danger, #ef4444);
}

.workspace-command-feedback__icon[data-status="cancelled"] {
  background: color-mix(in srgb, var(--color-warning, #f59e0b) 14%, transparent);
  color: var(--color-warning, #f59e0b);
}

.workspace-command-feedback__body {
  display: grid;
  flex: 1 1 auto;
  gap: var(--space-2);
  min-width: 0;
}

.workspace-command-feedback__header {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}

.workspace-command-feedback__header strong {
  color: var(--color-text-primary);
  font: var(--font-label-md);
}

.workspace-command-feedback__header span {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  overflow-wrap: anywhere;
  white-space: normal;
}

.workspace-command-feedback__progress {
  background: var(--color-bg-subtle);
  border-radius: 999px;
  height: 6px;
  overflow: hidden;
}

.workspace-command-feedback__progress span {
  background: var(--color-brand-primary);
  display: block;
  height: 100%;
  transition: width var(--motion-content) var(--ease-standard);
}

.workspace-command-feedback__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: flex-end;
}

.workspace-command-feedback__button {
  align-items: center;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  cursor: pointer;
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-2);
  min-height: 32px;
  padding: 0 var(--space-3);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce);
}

.workspace-command-feedback__button--primary {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}

.workspace-command-feedback__button:not(:disabled):hover {
  border-color: var(--color-brand-primary);
  transform: translateY(-1px);
}

.workspace-command-feedback__button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.workspace-command-feedback__button .material-symbols-outlined {
  font-size: 18px;
}

@container editing-workspace (max-width: 760px) {
  .workspace-command-feedback {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .workspace-command-feedback__actions {
    flex: 1 1 100%;
    justify-content: flex-start;
  }
}
</style>
