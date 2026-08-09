<template>
  <section class="sk-card" data-testid="positioning-panel">
    <header class="sk-card__header">
      <div>
        <p class="sk-eyebrow">账号定位</p>
        <h2>内容方向</h2>
      </div>
      <button
        v-if="!cache.positioningEditorOpen && cache.pageState !== 'first_use'"
        class="sk-button sk-button--secondary"
        type="button"
        @click="emit('open-editor')"
      >
        新建版本
      </button>
    </header>

    <div v-if="activeVersion" class="sk-active-summary">
      <span class="sk-status-dot sk-status-dot--ready" aria-hidden="true" />
      <div class="sk-active-summary__body">
        <div class="sk-active-summary__heading">
          <strong>当前定位</strong>
          <span class="sk-pill sk-pill--active">v{{ activeVersion }} 使用中</span>
        </div>
        <p>{{ activeSummary }}</p>
        <div v-if="activeToneTags.length" class="sk-tag-row">
          <span v-for="tag in activeToneTags" :key="tag">#{{ tag }}</span>
        </div>
        <div class="sk-compact-actions">
          <button
            class="sk-button sk-button--text"
            type="button"
            @click="emit('open-detail', activeVersion)"
          >
            查看详情
          </button>
          <button
            class="sk-button sk-button--text"
            type="button"
            @click="emit('edit-version', activeVersion)"
          >
            编辑定位
          </button>
        </div>
      </div>
    </div>
    <div v-else class="sk-inline-empty">
      <span class="material-symbols-outlined" aria-hidden="true">target</span>
      <p>
        {{ cache.positioning?.versions.length
          ? "尚未选择使用中的定位，请查看草稿后确认启用。"
          : "尚未创建定位。先创建草稿，再确认启用。" }}
      </p>
    </div>

    <PositioningEditor
      v-if="cache.positioningEditorOpen"
      :cache="cache"
      @cancel="emit('cancel-editor')"
      @create="emit('create')"
      @update="updateDraft"
    />

    <div v-if="cache.positioning?.versions.length" class="sk-version-list">
      <article
        v-for="item in cache.positioning.versions"
        :key="item.version"
        class="sk-version-row"
      >
        <button
          class="sk-version-row__main"
          type="button"
          :aria-label="`查看定位版本 v${item.version} 详情`"
          @click="emit('open-detail', item.version)"
        >
          <div class="sk-version-row__heading">
            <strong>v{{ item.version }}</strong>
            <span :class="`sk-pill sk-pill--${item.status}`">
              {{ statusLabel(item.status) }}
            </span>
          </div>
          <p>{{ item.summary }}</p>
        </button>
        <div class="sk-version-row__end">
          <time>{{ formatKnowledgeDate(item.createdAt) }}</time>
          <div class="sk-compact-actions">
            <button
              class="sk-button sk-button--text"
              type="button"
              @click="emit('open-detail', item.version)"
            >
              查看详情
            </button>
            <button
              v-if="item.status === 'draft'"
              class="sk-button sk-button--text"
              type="button"
              :disabled="Boolean(cache.busyKey)"
              @click="emit('activate', item.version)"
            >
              设为使用中
            </button>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  AccountKnowledgeCache,
  PositioningDraft
} from "./account-knowledge-types";
import { formatKnowledgeDate } from "./knowledge-view-helpers";
import PositioningEditor from "./PositioningEditor.vue";
import { positioningToneTags } from "./positioning-view-helpers";

const props = defineProps<{ cache: AccountKnowledgeCache }>();
const emit = defineEmits<{
  "open-editor": [];
  "cancel-editor": [];
  "open-detail": [version: number];
  "edit-version": [version: number];
  create: [];
  activate: [version: number];
  "update-draft": [field: keyof PositioningDraft, value: string];
}>();

const activeVersion = computed(() =>
  props.cache.positioning?.activeVersion ?? null
);
const activeSummary = computed(() =>
  props.cache.positioning?.versions.find(
    (item) => item.version === activeVersion.value
  )?.summary ?? "定位版本已激活"
);
const activeToneTags = computed(() => {
  const detail = props.cache.positioningDetail;
  return detail?.version === activeVersion.value
    ? positioningToneTags(detail.tone)
    : [];
});

function statusLabel(status: string): string {
  return status === "active" ? "使用中" : status === "draft" ? "草稿" : "已归档";
}

function updateDraft(field: keyof PositioningDraft, value: string): void {
  emit("update-draft", field, value);
}
</script>
