<template>
  <section class="ai-execution-workspace">
    <header class="ai-execution-workspace__header">
      <div>
        <span class="recipe-eyebrow">AI Execution Gateway</span>
        <h3>真实调用验证</h3>
      </div>
      <button
        type="button"
        class="ai-execution-link"
        :disabled="Boolean(cache.busyKey)"
        @click="store.load(accountId)"
      >
        刷新
      </button>
    </header>

    <div v-if="cache.feedback" class="ai-execution-feedback">
      <span>{{ cache.feedback }}</span>
      <button type="button" @click="store.clearFeedback(accountId)">×</button>
    </div>
    <div v-if="cache.error" class="ai-execution-feedback is-error">
      <span>{{ cache.error.message }}</span>
      <button
        v-if="cache.error.logId"
        type="button"
        @click="$emit('openLog', cache.error.logId)"
      >
        日志
      </button>
    </div>

    <form class="ai-execution-launcher" @submit.prevent="runExecution">
      <label class="is-wide">
        <span>验证主题</span>
        <input
          v-model="cache.topic"
          maxlength="500"
          placeholder="输入本次脚本生成主题"
          :disabled="restricted"
        />
      </label>
      <label>
        <span>知识快照</span>
        <select
          :value="cache.selectedKnowledgeSnapshotId"
          :disabled="restricted || !cache.knowledgeSnapshots.length"
          @change="selectSnapshot"
        >
          <option value="" disabled>
            {{ cache.knowledgeSnapshots.length ? "选择快照" : "尚无可用快照" }}
          </option>
          <option
            v-for="snapshot in cache.knowledgeSnapshots"
            :key="snapshot.id"
            :value="snapshot.id"
          >
            {{ snapshot.label || shortHash(snapshot.contentHash) }}
          </option>
        </select>
      </label>
      <label>
        <span>最长费用（微单位）</span>
        <input
          v-model.number="cache.policy.maxCostMicros"
          type="number"
          min="0"
          step="1000"
          :disabled="restricted"
        />
      </label>
      <div class="ai-execution-launcher__actions">
        <button
          type="button"
          class="ai-execution-button is-secondary"
          :disabled="restricted || Boolean(cache.busyKey)"
          @click="runPreflight"
        >
          {{ cache.busyKey === "preflight" ? "预检中…" : "预检" }}
        </button>
        <button
          type="submit"
          class="ai-execution-button is-primary"
          :disabled="restricted || Boolean(cache.busyKey)"
        >
          {{ cache.busyKey === "create" ? "提交中…" : "运行真实调用" }}
        </button>
      </div>
    </form>

    <div
      v-if="cache.preflight"
      :class="['ai-execution-preflight', { 'is-blocked': !cache.preflight.ready }]"
    >
      <div class="ai-execution-preflight__summary">
        <span>候选 {{ cache.preflight.candidateCount }}</span>
        <span>预算 {{ cache.preflight.costEstimate.maximumMicros ?? "待确认" }}</span>
        <span>快照 {{ shortHash(cache.preflight.snapshotPreviewHash) }}</span>
      </div>
      <ul v-if="cache.preflight.blockingIssues.length">
        <li v-for="issue in cache.preflight.blockingIssues" :key="`${issue.code}:${issue.path}`">
          <strong>{{ issue.code }}</strong>
          <span>{{ issue.message }}</span>
        </li>
      </ul>
      <div v-if="cache.preflight.repairActions.length" class="ai-execution-preflight__actions">
        <button
          v-for="action in cache.preflight.repairActions"
          :key="`${action.targetPage}:${action.targetSection}:${action.targetResourceId ?? ''}`"
          type="button"
          class="ai-execution-link"
          @click="handleRepair(action)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>

    <div class="ai-execution-workspace__body">
      <AIExecutionStatePanel
        :state="cache.state"
        :items="cache.executions"
        :selected-id="cache.selectedExecutionId"
        :error-message="cache.error?.message"
        @refresh="store.load(accountId)"
        @select="store.selectExecution(accountId, $event)"
      />
      <AIExecutionDetailPanel
        :detail="cache.detail"
        :output-content="cache.outputContent"
        :busy="Boolean(cache.busyKey)"
        @cancel="store.cancel(accountId, $event)"
        @retry="store.retry(accountId, $event)"
        @load-output="loadOutput"
        @open-log="$emit('openLog', $event)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, watch } from "vue";
import { routerKey } from "vue-router";

import type { AIExecutionRepairActionDto } from "@/types/runtime/ai-executions";
import { routeIds } from "@/app/router/route-ids";

import { executionError, shortHash } from "../ai-execution-helpers";
import { useAIExecutionStore } from "../ai-execution-store";
import AIExecutionDetailPanel from "./AIExecutionDetailPanel.vue";
import AIExecutionStatePanel from "./AIExecutionStatePanel.vue";
import "../styles/ai-execution.css";

const props = defineProps<{
  accountId: string;
  accountRevision: number;
  recipeVersionId: string;
  restricted?: boolean;
}>();

const emit = defineEmits<{
  openLog: [logId: string];
  repair: [action: AIExecutionRepairActionDto];
}>();

const store = useAIExecutionStore();
const router = inject(routerKey, null);
const cache = computed(() => store.cache(props.accountId));

watch(
  () => props.accountId,
  (accountId) => void store.load(accountId)
);

onMounted(() => void store.load(props.accountId));
onUnmounted(() => store.stopAccount(props.accountId, true));

function selectSnapshot(event: Event): void {
  store.selectKnowledgeSnapshot(
    props.accountId,
    (event.target as HTMLSelectElement).value
  );
}

function runPreflight(): void {
  void store.runPreflight(
    props.accountId,
    props.accountRevision,
    props.recipeVersionId
  );
}

function runExecution(): void {
  void store.create(
    props.accountId,
    props.accountRevision,
    props.recipeVersionId
  );
}

function loadOutput(outputId: string): void {
  const detail = cache.value.detail;
  if (detail) void store.loadOutput(props.accountId, detail.id, outputId);
}

function handleRepair(action: AIExecutionRepairActionDto): void {
  emit("repair", action);
  if (
    !router
    || !["ai-system-settings", "ai_system_settings"].includes(action.targetPage)
  ) return;
  void router.push({
    name: routeIds.aiSystemSettings,
    query: {
      section: action.targetSection,
      resource: action.targetResourceId ?? undefined
    }
  }).catch((error) => {
    cache.value.error = executionError(error, "无法打开 AI 修复入口。");
  });
}
</script>
