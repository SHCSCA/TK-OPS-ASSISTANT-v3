<template>
  <div
    v-if="feedback"
    class="account-status-feedback"
    :data-tone="feedback.tone"
    role="status"
  >
    <span class="account-status-feedback__message">
      <span class="material-symbols-outlined">{{ icon }}</span>
      <span>{{ feedback.message }}</span>
    </span>
    <span class="account-status-feedback__actions">
      <button
        v-if="feedback.retryable"
        type="button"
        @click="emit('retry', feedback.id)"
      >
        重试
      </button>
      <button
        v-if="feedback.logId"
        type="button"
        @click="emit('openLog', feedback.logId)"
      >
        查看日志
      </button>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ShellFeedback } from "./account-workspace-types";

const props = defineProps<{
  feedback: ShellFeedback | null;
}>();

const emit = defineEmits<{
  openLog: [logId: string];
  retry: [feedbackId: string];
}>();

const icon = computed(() => {
  switch (props.feedback?.tone) {
    case "danger":
      return "error";
    case "warning":
      return "warning";
    default:
      return "info";
  }
});
</script>
