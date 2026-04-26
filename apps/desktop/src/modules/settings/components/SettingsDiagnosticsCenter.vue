<template>
  <section class="settings-diagnostics-center" data-testid="settings-inline-diagnostics">
    <header class="settings-diagnostics-center__header">
      <div>
        <p class="detail-panel__label">检测中心</p>
        <h2>系统运行必需项检测</h2>
        <p class="workspace-page__summary">
          检测结果来自 Runtime，覆盖授权、目录、媒体工具、AI Provider 和任务通道。
        </p>
      </div>
      <button
        class="settings-diagnostics-center__button"
        type="button"
        data-action="run-system-diagnostics"
        :disabled="loading"
        @click="$emit('run')"
      >
        {{ loading ? "检测中..." : "一键检测" }}
      </button>
    </header>

    <div v-if="errorMessage" class="settings-diagnostics-center__alert" data-tone="failed">
      {{ errorMessage }}
    </div>

    <div v-if="!report" class="settings-diagnostics-center__empty">
      <strong>尚未获得检测报告</strong>
      <span>点击“一键检测”后，系统会返回当前运行所需配置的真实状态。</span>
    </div>

    <template v-else>
      <div class="settings-diagnostics-center__summary" :data-status="report.overallStatus">
        <span>{{ overallLabel }}</span>
        <strong>{{ statusText(report.overallStatus) }}</strong>
        <small>上次检测 {{ formatCheckedAt(report.checkedAt) }}</small>
      </div>

      <div class="settings-diagnostics-center__groups">
        <section
          v-for="group in groupedItems"
          :key="group.group"
          class="settings-diagnostics-center__group"
        >
          <h3>{{ group.group }}</h3>
          <article
            v-for="item in group.items"
            :key="item.id"
            class="settings-diagnostics-center__item"
            :data-status="item.status"
          >
            <div class="settings-diagnostics-center__item-head">
              <span>{{ item.label }}</span>
              <strong>{{ statusText(item.status) }}</strong>
            </div>
            <p>{{ item.summary }}</p>
            <small>{{ item.impact }}</small>
            <code v-if="item.detail">{{ item.detail }}</code>
            <em v-if="item.actionLabel">{{ item.actionLabel }}</em>
          </article>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  RuntimeDiagnosticItem,
  RuntimeDiagnosticStatus,
  RuntimeDiagnostics
} from "@/types/runtime";

const props = defineProps<{
  errorMessage: string;
  loading: boolean;
  report: RuntimeDiagnostics | null;
}>();

defineEmits<{
  (e: "run"): void;
}>();

const groupedItems = computed(() => {
  const groups = new Map<string, RuntimeDiagnosticItem[]>();
  for (const item of props.report?.items ?? []) {
    groups.set(item.group, [...(groups.get(item.group) ?? []), item]);
  }
  return [...groups.entries()].map(([group, items]) => ({ group, items }));
});

const overallLabel = computed(() => {
  const total = props.report?.items.length ?? 0;
  const warnings = props.report?.items.filter((item) => item.status === "warning").length ?? 0;
  const failed = props.report?.items.filter((item) => item.status === "failed").length ?? 0;
  return `${total} 项检测 · ${warnings} 项警告 · ${failed} 项失败`;
});

function statusText(status: RuntimeDiagnosticStatus): string {
  if (status === "ready") return "正常";
  if (status === "warning") return "需处理";
  return "失败";
}

function formatCheckedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未知";
  return date.toLocaleString("zh-CN");
}
</script>

<style scoped>
.settings-diagnostics-center {
  display: grid;
  gap: var(--density-panel-gap);
  padding: var(--space-5);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--surface-secondary) 96%, transparent);
}

.settings-diagnostics-center__header,
.settings-diagnostics-center__item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.settings-diagnostics-center__header h2,
.settings-diagnostics-center__group h3 {
  margin: 0;
}

.settings-diagnostics-center__button {
  min-height: 36px;
  padding: 0 var(--space-4);
  border: 1px solid color-mix(in srgb, var(--brand-primary) 42%, var(--border-default));
  border-radius: var(--radius-sm);
  background: var(--brand-primary);
  color: var(--text-inverse);
  cursor: pointer;
  font: var(--font-title-sm);
}

.settings-diagnostics-center__button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.settings-diagnostics-center__alert,
.settings-diagnostics-center__empty,
.settings-diagnostics-center__summary,
.settings-diagnostics-center__item {
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--surface-tertiary) 88%, transparent);
}

.settings-diagnostics-center__alert[data-tone="failed"] {
  color: var(--status-error);
  border-color: color-mix(in srgb, var(--status-error) 32%, var(--border-default));
}

.settings-diagnostics-center__summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.settings-diagnostics-center__summary[data-status="ready"] strong {
  color: var(--status-success);
}

.settings-diagnostics-center__summary[data-status="warning"] strong {
  color: var(--status-warning);
}

.settings-diagnostics-center__summary[data-status="failed"] strong {
  color: var(--status-error);
}

.settings-diagnostics-center__groups {
  display: grid;
  gap: var(--space-4);
}

.settings-diagnostics-center__group {
  display: grid;
  gap: var(--space-3);
}

.settings-diagnostics-center__item {
  display: grid;
  gap: var(--space-2);
}

.settings-diagnostics-center__item[data-status="warning"] {
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--border-default));
}

.settings-diagnostics-center__item[data-status="failed"] {
  border-color: color-mix(in srgb, var(--status-error) 30%, var(--border-default));
}

.settings-diagnostics-center__item p,
.settings-diagnostics-center__item small,
.settings-diagnostics-center__empty span {
  margin: 0;
  color: var(--text-secondary);
}

.settings-diagnostics-center__item code {
  white-space: pre-wrap;
  color: var(--text-secondary);
  font: var(--font-caption);
}

.settings-diagnostics-center__item em {
  color: var(--brand-primary);
  font-style: normal;
  font-weight: 700;
}
</style>
