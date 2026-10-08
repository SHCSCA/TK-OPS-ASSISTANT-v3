<template>
  <aside class="ai-execution-detail" aria-label="AI 执行详情">
    <div v-if="!detail" class="ai-execution-state">
      <span class="material-symbols-outlined">select_check_box</span>
      <span>选择一条执行查看详情</span>
    </div>
    <template v-else>
      <header>
        <div>
          <small>真实 AI 执行</small>
          <h4>{{ executionStatusLabel(detail.status, detail.failureKind, detail.completionKind) }}</h4>
        </div>
        <span :class="['ai-execution-badge', `is-${detail.status}`]">
          {{ Math.round(detail.progress * 100) }}%
        </span>
      </header>

      <div v-if="detail.failureKind === 'result_unknown'" class="ai-execution-warning">
        远端可能已产生调用与费用，请确认后再按原快照重试。
      </div>
      <div v-else-if="detail.errorCode" class="ai-execution-warning">
        {{ latestError?.safeSummary || detail.errorCode }}
        <button
          v-if="detail.logId"
          type="button"
          class="ai-execution-link"
          @click="$emit('openLog', detail.logId)"
        >
          日志
        </button>
      </div>

      <dl class="ai-execution-metrics">
        <div><dt>候选</dt><dd>{{ detail.candidates.length }}</dd></div>
        <div><dt>尝试</dt><dd>{{ detail.jobs.length }}</dd></div>
        <div><dt>用量</dt><dd>{{ totalUnits }}</dd></div>
        <div><dt>费用</dt><dd>{{ costText }}</dd></div>
      </dl>

      <section v-if="detail.outputs.length" class="ai-execution-output">
        <header>
          <strong>输出</strong>
          <button
            v-if="!detail.outputs[0]?.quarantined"
            type="button"
            class="ai-execution-link"
            @click="$emit('loadOutput', detail.outputs[0]!.id)"
          >
            查看正文
          </button>
        </header>
        <pre v-if="outputContent">{{ outputContent }}</pre>
        <span v-else>{{ shortHash(detail.outputs[0]?.contentHash) }}</span>
      </section>

      <details v-if="detail.jobs.length" class="ai-execution-technical">
        <summary>尝试记录</summary>
        <table>
          <thead><tr><th>次序</th><th>状态</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="job in detail.jobs" :key="job.id">
              <td>{{ job.attempt }}</td>
              <td>{{ executionStatusLabel(job.status, job.failureKind, job.completionKind) }}</td>
              <td>{{ job.durationMs === null ? "—" : `${job.durationMs}ms` }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <details class="ai-execution-technical">
        <summary>冻结快照</summary>
        <dl>
          <div><dt>快照</dt><dd>{{ shortHash(detail.snapshotHash) }}</dd></div>
          <div><dt>配置修订</dt><dd>{{ snapshotRevision }}</dd></div>
          <div><dt>重试来源</dt><dd>{{ detail.retryOfExecutionId || "—" }}</dd></div>
        </dl>
      </details>

      <footer>
        <button
          v-if="detail.availableActions.includes('cancel')"
          type="button"
          class="ai-execution-button is-secondary"
          :disabled="busy"
          @click="$emit('cancel', detail.id)"
        >
          取消
        </button>
        <button
          v-if="detail.availableActions.includes('retry_same_snapshot')"
          type="button"
          class="ai-execution-button is-primary"
          :disabled="busy"
          @click="$emit('retry', detail.id)"
        >
          按原快照重试
        </button>
      </footer>
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { AIExecutionDetailDto } from "@/types/runtime/ai-executions";

import {
  costLabel,
  executionStatusLabel,
  shortHash
} from "../ai-execution-helpers";

const props = defineProps<{
  detail: AIExecutionDetailDto | null;
  outputContent: string | null;
  busy: boolean;
}>();

defineEmits<{
  cancel: [executionId: string];
  retry: [executionId: string];
  loadOutput: [outputId: string];
  openLog: [logId: string];
}>();

const latestUsage = computed(() => props.detail?.usage.at(-1) ?? null);
const latestError = computed(() => props.detail?.errors.at(-1) ?? null);
const totalUnits = computed(() => latestUsage.value?.totalUnits ?? "—");
const costText = computed(() => costLabel(
  props.detail?.costMicros ?? null,
  latestUsage.value?.currency ?? "USD",
  props.detail?.costStatus ?? "unavailable"
));
const snapshotRevision = computed(() => {
  const value = props.detail?.snapshot.aiConfigRevision;
  return typeof value === "number" ? value : "—";
});
</script>
