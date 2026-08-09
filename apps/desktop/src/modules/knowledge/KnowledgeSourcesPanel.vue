<template>
  <section
    class="sk-card sk-card--wide"
    data-testid="knowledge-sources-panel"
    :data-state="cache.sourceState"
  >
    <header class="sk-card__header sk-card__header--wrap">
      <div>
        <p class="sk-eyebrow">内容来源</p>
        <h2>知识来源</h2>
      </div>
      <div class="sk-header-actions">
        <button
          class="sk-button sk-button--secondary"
          type="button"
          :disabled="Boolean(cache.busyKey) || !hasIndexableSources"
          @click="$emit('start-index')"
        >
          <span class="material-symbols-outlined" aria-hidden="true">sync</span>
          索引可用来源
        </button>
        <button
          v-if="!cache.sourceEditorOpen"
          class="sk-button sk-button--primary"
          type="button"
          @click="$emit('open-editor')"
        >
          添加来源
        </button>
      </div>
    </header>

    <div class="sk-blocked-note" data-state="dependency_blocked">
      <span class="material-symbols-outlined" aria-hidden="true">folder_off</span>
      <p>本地文件将在 P0-F 通过受控文件桥接入；当前仅接受文本与公共 HTTPS 网址，不接收本地路径。</p>
    </div>

    <form
      v-if="cache.sourceEditorOpen"
      class="sk-source-form"
      data-testid="source-editor"
      @submit.prevent="$emit('add-source')"
    >
      <div class="sk-segmented" role="group" aria-label="来源类型">
        <button
          v-for="mode in availableModes"
          :key="mode.value"
          type="button"
          :class="{ 'is-active': cache.sourceDraft.mode === mode.value }"
          @click="$emit('update-draft', 'mode', mode.value)"
        >
          {{ mode.label }}
        </button>
        <button type="button" disabled title="等待 P0-F 受控文件桥">
          本地文件
        </button>
      </div>
      <div class="sk-field-grid">
        <label class="sk-field">
          <span>标题</span>
          <input
            :value="cache.sourceDraft.title"
            maxlength="256"
            placeholder="便于识别的来源名称"
            @input="updateText('title', $event)"
          />
        </label>
        <label v-if="cache.sourceDraft.mode === 'url'" class="sk-field">
          <span>公共 HTTPS 网址</span>
          <input
            :value="cache.sourceDraft.url"
            inputmode="url"
            placeholder="https://example.com/article"
            @input="updateText('url', $event)"
          />
        </label>
      </div>
      <label v-if="cache.sourceDraft.mode === 'text'" class="sk-field">
        <span>文本内容</span>
        <textarea
          :value="cache.sourceDraft.text"
          rows="5"
          placeholder="粘贴已获授权的知识文本；正文不会在列表中回显"
          @input="updateText('text', $event)"
        />
      </label>
      <div class="sk-actions">
        <button
          class="sk-button sk-button--ghost"
          type="button"
          @click="$emit('cancel-editor')"
        >
          取消
        </button>
        <button
          class="sk-button sk-button--primary"
          type="submit"
          :disabled="Boolean(cache.busyKey)"
        >
          {{ cache.busyKey === "source-add" ? "添加中…" : "添加来源" }}
        </button>
      </div>
    </form>

    <div class="sk-source-toolbar">
      <label>
        <span>类型</span>
        <select
          :value="cache.sourceFilters.kind"
          @change="changeFilter('kind', $event)"
        >
          <option value="">全部</option>
          <option v-for="(label, kind) in sourceKindLabels" :key="kind" :value="kind">
            {{ label }}
          </option>
        </select>
      </label>
      <label>
        <span>状态</span>
        <select
          :value="cache.sourceFilters.status"
          @change="changeFilter('status', $event)"
        >
          <option value="">全部</option>
          <option
            v-for="(label, status) in sourceStatusLabels"
            :key="status"
            :value="status"
          >
            {{ label }}
          </option>
        </select>
      </label>
      <span v-if="cache.sourceTotalKnown !== null" class="sk-source-total">
        {{ cache.sourceTotalKnown }} 项
      </span>
    </div>

    <div
      v-if="cache.sourceState === 'loading'"
      class="sk-list-state"
      data-state="loading"
    >
      <span class="sk-spinner" aria-hidden="true" />
      正在读取知识来源…
    </div>
    <div
      v-else-if="cache.sourceState === 'filtered_empty'"
      class="sk-list-state"
      data-state="filtered_empty"
    >
      当前筛选下没有来源。
    </div>
    <div
      v-else-if="cache.sourceState === 'empty'"
      class="sk-list-state"
      data-state="empty"
    >
      暂无来源。添加文本或网址后再提交索引。
    </div>
    <div v-else class="sk-source-table-wrap">
      <table class="sk-source-table">
        <thead>
          <tr>
            <th>来源</th>
            <th>类型</th>
            <th>状态</th>
            <th>最近索引</th>
            <th><span class="sr-only">操作</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in cache.sources" :key="source.id">
            <td>
              <strong>{{ source.title }}</strong>
              <small v-if="source.sourceUrl">{{ source.sourceUrl }}</small>
              <small v-if="source.errorCode" class="sk-error-code">
                {{ source.errorCode }}
                <template v-if="source.logId"> · 日志 {{ source.logId }}</template>
              </small>
            </td>
            <td>{{ sourceKindLabels[source.kind] }}</td>
            <td>
              <span :class="`sk-source-status sk-source-status--${source.status}`">
                {{ sourceStatusLabels[source.status] }}
              </span>
            </td>
            <td>{{ formatKnowledgeDate(source.indexedAt) }}</td>
            <td>
              <div class="sk-row-actions">
                <button
                  v-if="!['removed', 'indexing'].includes(source.status)"
                  class="sk-button sk-button--text"
                  type="button"
                  :disabled="Boolean(cache.busyKey)"
                  @click="$emit('index-source', source.id)"
                >
                  索引
                </button>
                <button
                  v-if="source.status !== 'removed'"
                  class="sk-button sk-button--text sk-button--danger"
                  type="button"
                  :disabled="Boolean(cache.busyKey)"
                  @click="$emit('remove-source', source.id)"
                >
                  移除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="cache.sourceState === 'waiting'"
      class="sk-waiting"
      data-state="waiting"
    >
      <span class="sk-spinner" aria-hidden="true" />
      <span>
        索引任务进行中
        <small v-if="cache.indexTaskId">任务 {{ cache.indexTaskId }}</small>
      </span>
      <button class="sk-button sk-button--text" type="button" @click="$emit('refresh')">
        刷新
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type {
  KnowledgeKind,
  KnowledgeSourceStatus
} from "@/types/runtime/account-knowledge";
import type {
  AccountKnowledgeCache,
  KnowledgeSourceDraft,
  KnowledgeSourceFilters
} from "./account-knowledge-types";
import {
  formatKnowledgeDate,
  sourceKindLabels,
  sourceStatusLabels
} from "./knowledge-view-helpers";

const props = defineProps<{ cache: AccountKnowledgeCache }>();
const emit = defineEmits<{
  "open-editor": [];
  "cancel-editor": [];
  "add-source": [];
  "start-index": [];
  "index-source": [sourceId: string];
  "remove-source": [sourceId: string];
  refresh: [];
  filter: [filters: KnowledgeSourceFilters];
  "update-draft": [
    field: keyof KnowledgeSourceDraft,
    value: KnowledgeSourceDraft[keyof KnowledgeSourceDraft]
  ];
}>();

const availableModes = [
  { value: "text" as const, label: "文本" },
  { value: "url" as const, label: "网址" }
];
const hasIndexableSources = computed(() => {
  const counts = props.cache.knowledge?.sourceCounts ?? {};
  return Object.entries(counts).some(
    ([status, count]) => status !== "removed" && count > 0
  );
});

function updateText(
  field: "title" | "url" | "text",
  event: Event
): void {
  emit("update-draft", field, (event.target as HTMLInputElement).value);
}

function changeFilter(field: "kind" | "status", event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (field === "kind") {
    emit("filter", {
      ...props.cache.sourceFilters,
      kind: value as KnowledgeKind | ""
    });
    return;
  }
  emit("filter", {
    ...props.cache.sourceFilters,
    status: value as KnowledgeSourceStatus | ""
  });
}
</script>
