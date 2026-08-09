<template>
  <section
    class="ai-state-panel"
    :class="`is-${state}`"
    :aria-busy="state === 'loading'"
  >
    <div v-if="state === 'loading'" class="ai-state-skeleton" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
    <span v-else class="material-symbols-outlined" aria-hidden="true">
      {{ descriptor.icon }}
    </span>
    <div>
      <h3>{{ title || descriptor.title }}</h3>
      <p>{{ description || errorMessage || descriptor.description }}</p>
      <small v-if="taskId">任务：{{ taskId }}</small>
      <small v-if="logId">日志：{{ logId }}</small>
    </div>
    <div class="ai-state-panel__actions">
      <button
        v-if="state === 'filtered_empty'"
        class="ai-button is-secondary"
        type="button"
        @click="$emit('clearFilters')"
      >
        清除筛选
      </button>
      <button
        v-if="state === 'waiting_external' && cancellable"
        class="ai-button is-secondary"
        type="button"
        @click="$emit('cancel')"
      >
        取消任务
      </button>
      <button
        v-if="state === 'error' || state === 'waiting_external'"
        class="ai-button is-secondary"
        type="button"
        @click="$emit('retry')"
      >
        {{ state === "waiting_external" ? "刷新状态" : "重试" }}
      </button>
      <button
        v-if="logId"
        class="ai-button is-quiet"
        type="button"
        @click="$emit('openLog', logId)"
      >
        查看日志
      </button>
      <button
        v-if="actionLabel"
        class="ai-button is-primary"
        type="button"
        @click="$emit('action')"
      >
        {{ actionLabel }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { stateDescriptor } from "../ai-config-helpers";
import type { AIPageState } from "../ai-config-types";

const props = withDefaults(defineProps<{
  actionLabel?: string;
  cancellable?: boolean;
  description?: string;
  errorMessage?: string | null;
  logId?: string | null;
  state: AIPageState;
  taskId?: string | null;
  title?: string;
}>(), {
  actionLabel: "",
  cancellable: false,
  description: "",
  errorMessage: null,
  logId: null,
  taskId: null,
  title: ""
});

defineEmits<{
  action: [];
  cancel: [];
  clearFilters: [];
  openLog: [logId: string];
  retry: [];
}>();

const descriptor = computed(() => stateDescriptor(props.state));
</script>
