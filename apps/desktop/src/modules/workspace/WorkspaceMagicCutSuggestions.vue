<template>
  <section
    class="workspace-magic-cut-suggestions"
    data-testid="magic-cut-suggestions"
    :data-status="status"
  >
    <div class="workspace-magic-cut-suggestions__header">
      <div>
        <strong>{{ title }}</strong>
        <p>{{ description }}</p>
      </div>
      <span v-if="status === 'loading' || status === 'applying'" class="material-symbols-outlined spinning">
        progress_activity
      </span>
    </div>

    <div v-if="status === 'loading'" class="workspace-magic-cut-suggestions__state" role="status">
      正在读取智能粗剪建议
    </div>

    <div v-else-if="status === 'error'" class="workspace-magic-cut-suggestions__state workspace-magic-cut-suggestions__state--error">
      <span>{{ errorMessage || "智能粗剪建议读取失败，请稍后重试。" }}</span>
      <button type="button" data-testid="magic-cut-reload" @click="emit('reload')">
        <span class="material-symbols-outlined">refresh</span>
        重新读取
      </button>
    </div>

    <div v-else-if="isFailedParse" class="workspace-magic-cut-suggestions__state workspace-magic-cut-suggestions__state--warning">
      <span>AI 返回内容无法生成建议，请重新生成</span>
      <button type="button" data-testid="magic-cut-regenerate" @click="emit('regenerate')">
        <span class="material-symbols-outlined">auto_awesome</span>
        重新生成
      </button>
    </div>

    <div v-else-if="!hasReviewableSuggestion" class="workspace-magic-cut-suggestions__state">
      暂无可应用建议。
    </div>

    <template v-else>
      <div
        class="workspace-magic-cut-suggestions__list"
        data-testid="magic-cut-operation-list"
      >
        <article
          v-for="operation in suggestion!.operations"
          :key="operation.id"
          class="workspace-magic-cut-suggestions__item"
          :data-testid="`magic-cut-operation-${operation.id}`"
        >
          <label class="workspace-magic-cut-suggestions__select">
            <input
              v-model="selectedOperationIds"
              :disabled="isApplying"
              :value="operation.id"
              type="checkbox"
            />
            <span>{{ actionLabel(operation.action) }}</span>
          </label>

          <div class="workspace-magic-cut-suggestions__item-body">
            <strong>{{ operation.clipId }}</strong>
            <p>{{ operation.reason || "AI 建议调整此片段以优化节奏。" }}</p>
            <dl>
              <div>
                <dt>原时间</dt>
                <dd>{{ originalTimeLabel(operation) }}</dd>
              </div>
              <div>
                <dt>建议</dt>
                <dd>{{ suggestedTimeLabel(operation) }}</dd>
              </div>
              <div v-if="operation.risk">
                <dt>风险</dt>
                <dd>{{ operation.risk }}</dd>
              </div>
            </dl>
          </div>

          <div class="workspace-magic-cut-suggestions__item-actions">
            <button
              type="button"
              :data-testid="`magic-cut-focus-${operation.id}`"
              @click="emit('focus', { clipId: operation.clipId, trackId: operation.trackId ?? null })"
            >
              <span class="material-symbols-outlined">my_location</span>
              定位片段
            </button>
            <button
              type="button"
              :data-testid="`magic-cut-apply-one-${operation.id}`"
              :disabled="isApplying"
              @click="emit('apply', [operation.id])"
            >
              <span class="material-symbols-outlined">done</span>
              应用单条
            </button>
          </div>
        </article>
      </div>

      <p class="workspace-magic-cut-suggestions__confirm">
        应用后将修改当前时间线，可通过撤销恢复。
      </p>

      <div
        class="workspace-magic-cut-suggestions__actions"
        data-testid="magic-cut-bulk-actions"
      >
        <button
          type="button"
          data-testid="magic-cut-apply-selected"
          :disabled="isApplying || selectedOperationIds.length === 0"
          @click="emit('apply', selectedOperationIds)"
        >
          <span class="material-symbols-outlined">playlist_add_check</span>
          应用选中建议
        </button>
        <button
          type="button"
          data-testid="magic-cut-apply-all"
          :disabled="isApplying"
          @click="emit('apply', [])"
        >
          <span class="material-symbols-outlined">done_all</span>
          应用全部建议
        </button>
        <button
          type="button"
          data-testid="magic-cut-dismiss"
          :disabled="isApplying"
          @click="emit('dismiss')"
        >
          <span class="material-symbols-outlined">block</span>
          忽略全部
        </button>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  MagicCutSuggestionDraftDto,
  MagicCutSuggestionOperationDto
} from "@/types/runtime";

type MagicCutSuggestionStatus = "idle" | "loading" | "ready" | "applying" | "error";

const props = defineProps<{
  suggestion: MagicCutSuggestionDraftDto | null;
  status: MagicCutSuggestionStatus;
  errorMessage: string | null;
}>();

const emit = defineEmits<{
  apply: [operationIds: string[]];
  dismiss: [];
  focus: [payload: { clipId: string; trackId?: string | null }];
  reload: [];
  regenerate: [];
}>();

const selectedOperationIds = ref<string[]>([]);

const isApplying = computed(() => props.status === "applying");
const isFailedParse = computed(() => props.suggestion?.status === "failed_parse");
const hasReviewableSuggestion = computed(() =>
  props.suggestion?.status === "pending_review" && props.suggestion.operations.length > 0
);

const title = computed(() => {
  if (hasReviewableSuggestion.value) {
    return `AI 粗剪建议 · ${props.suggestion!.operations.length} 条待审阅`;
  }
  if (props.status === "applying") return "正在应用建议";
  return "AI 粗剪建议";
});

const description = computed(() => {
  if (props.status === "applying") return "正在应用建议";
  if (props.suggestion?.summary) return props.suggestion.summary;
  return "AI 建议必须经确认后才会修改时间线。";
});

watch(
  () => props.suggestion?.operations.map((operation) => operation.id).join("|") ?? "",
  () => {
    selectedOperationIds.value = props.suggestion?.operations.map((operation) => operation.id) ?? [];
  },
  { immediate: true }
);

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    delete: "删除",
    move: "移动",
    split: "分割",
    trim: "裁剪"
  };
  return labels[action] ?? action;
}

function originalTimeLabel(operation: MagicCutSuggestionOperationDto): string {
  if (operation.splitAtMs !== null && operation.splitAtMs !== undefined) {
    return `分割点 ${formatMs(operation.splitAtMs)}`;
  }
  const start = operation.originalStartMs ?? null;
  const duration = operation.originalDurationMs ?? null;
  if (start === null && duration === null) return "未标明";
  return `${start === null ? "未知起点" : formatMs(start)} · ${duration === null ? "未知时长" : formatMs(duration)}`;
}

function suggestedTimeLabel(operation: MagicCutSuggestionOperationDto): string {
  if (operation.targetTrackId) return `目标轨道 ${operation.targetTrackId}`;
  if (operation.splitAtMs !== null && operation.splitAtMs !== undefined) {
    return `在 ${formatMs(operation.splitAtMs)} 分割`;
  }
  const start = operation.suggestedStartMs ?? null;
  const duration = operation.suggestedDurationMs ?? null;
  if (start === null && duration === null) return "按建议移除或保持 Runtime 默认处理";
  return `${start === null ? "保持起点" : formatMs(start)} · ${duration === null ? "保持时长" : formatMs(duration)}`;
}

function formatMs(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
</script>

<style scoped>
.workspace-magic-cut-suggestions {
  display: grid;
  gap: var(--space-3);
  min-height: 0;
  min-width: 0;
}

.workspace-magic-cut-suggestions__header {
  align-items: start;
  display: flex;
  gap: var(--space-2);
  justify-content: space-between;
  min-width: 0;
}

.workspace-magic-cut-suggestions__header strong {
  color: var(--color-text-primary);
  font: var(--font-label-md);
}

.workspace-magic-cut-suggestions__header p,
.workspace-magic-cut-suggestions__confirm {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  margin: var(--space-1) 0 0;
  overflow-wrap: anywhere;
}

.workspace-magic-cut-suggestions__header .material-symbols-outlined {
  color: var(--color-brand-primary);
  flex: 0 0 auto;
  font-size: 18px;
}

.workspace-magic-cut-suggestions__state {
  background: var(--color-bg-subtle);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  display: grid;
  gap: var(--space-2);
  font: var(--font-body-sm);
  padding: var(--space-3);
}

.workspace-magic-cut-suggestions__state--error {
  border-color: color-mix(in srgb, var(--color-danger, #ef4444) 44%, var(--color-border-default));
}

.workspace-magic-cut-suggestions__state--warning {
  border-color: color-mix(in srgb, var(--color-warning, #f59e0b) 44%, var(--color-border-default));
}

.workspace-magic-cut-suggestions__list {
  display: grid;
  gap: var(--space-2);
  max-height: min(360px, 42vh);
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.workspace-magic-cut-suggestions__item {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-3);
}

.workspace-magic-cut-suggestions__select {
  align-items: center;
  color: var(--color-text-primary);
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-2);
  min-width: 0;
}

.workspace-magic-cut-suggestions__select input {
  accent-color: var(--color-brand-primary);
  flex: 0 0 auto;
}

.workspace-magic-cut-suggestions__item-body {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.workspace-magic-cut-suggestions__item-body strong {
  color: var(--color-text-primary);
  font: var(--font-label-sm);
  overflow-wrap: anywhere;
}

.workspace-magic-cut-suggestions__item-body p {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  margin: 0;
  overflow-wrap: anywhere;
}

.workspace-magic-cut-suggestions__item-body dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.workspace-magic-cut-suggestions__item-body dl div {
  display: grid;
  gap: 2px;
}

.workspace-magic-cut-suggestions__item-body dt {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
}

.workspace-magic-cut-suggestions__item-body dd {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  margin: 0;
  overflow-wrap: anywhere;
}

.workspace-magic-cut-suggestions__item-actions,
.workspace-magic-cut-suggestions__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  min-width: 0;
}

.workspace-magic-cut-suggestions button {
  align-items: center;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  cursor: pointer;
  display: inline-flex;
  font: var(--font-label-sm);
  gap: var(--space-1);
  min-height: 32px;
  padding: 0 var(--space-3);
  white-space: normal;
}

.workspace-magic-cut-suggestions__actions button:first-child,
.workspace-magic-cut-suggestions__actions button:nth-child(2) {
  background: var(--color-brand-primary);
  border-color: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}

.workspace-magic-cut-suggestions button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.workspace-magic-cut-suggestions button .material-symbols-outlined {
  flex: 0 0 auto;
  font-size: 17px;
}

@container editing-workspace (max-width: 420px) {
  .workspace-magic-cut-suggestions__actions,
  .workspace-magic-cut-suggestions__item-actions {
    align-items: stretch;
  }

  .workspace-magic-cut-suggestions button {
    flex: 1 1 136px;
    justify-content: center;
  }

  .workspace-magic-cut-suggestions__list {
    max-height: 280px;
  }
}
</style>
