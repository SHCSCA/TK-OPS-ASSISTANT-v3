<template>
  <section class="ai-execution-list" aria-label="AI 执行记录">
    <header>
      <strong>最近执行</strong>
      <button type="button" class="ai-execution-link" @click="$emit('refresh')">
        刷新
      </button>
    </header>

    <div v-if="state === 'loading'" class="ai-execution-state is-loading">
      <span class="material-symbols-outlined">progress_activity</span>
      <span>正在读取</span>
    </div>
    <div v-else-if="state === 'first_use'" class="ai-execution-state">
      <span class="material-symbols-outlined">auto_awesome</span>
      <span>尚无真实执行记录</span>
    </div>
    <div v-else-if="state === 'error' || state === 'restricted'" class="ai-execution-state is-error">
      <span class="material-symbols-outlined">error</span>
      <span>{{ errorMessage || "执行记录暂不可用" }}</span>
    </div>
    <div v-else class="ai-execution-list__items">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        :class="[
          `is-${item.status}`,
          { 'is-selected': item.id === selectedId }
        ]"
        @click="$emit('select', item.id)"
      >
        <span class="ai-execution-status-dot" aria-hidden="true"></span>
        <span>
          <strong>{{ executionStatusLabel(item.status, item.failureKind, item.completionKind) }}</strong>
          <small>{{ shortHash(item.snapshotHash) }}</small>
        </span>
        <time>{{ formatTime(item.updatedAt) }}</time>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AIExecutionSummaryDto } from "@/types/runtime/ai-executions";

import {
  executionStatusLabel,
  shortHash
} from "../ai-execution-helpers";
import type { AIExecutionViewState } from "../ai-execution-store";

defineProps<{
  state: AIExecutionViewState;
  items: AIExecutionSummaryDto[];
  selectedId: string | null;
  errorMessage?: string | null;
}>();

defineEmits<{
  refresh: [];
  select: [executionId: string];
}>();

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit"
    }).format(date);
}
</script>
