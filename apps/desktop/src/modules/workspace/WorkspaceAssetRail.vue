<template>
  <aside class="workspace-asset-rail" aria-label="工作台素材来源">
    <div class="workspace-asset-rail__heading">
      <span class="material-symbols-outlined">inventory_2</span>
      <div>
        <strong>片段来源</strong>
        <p>只展示当前时间线已经接入的真实片段来源。</p>
      </div>
    </div>

    <div class="workspace-asset-rail__summary">
      <small>当前来源</small>
      <strong>{{ summaryTitle }}</strong>
      <p>{{ summaryDescription }}</p>
    </div>

    <div v-if="!timeline" class="workspace-asset-rail__empty">
      还没有时间线草稿，素材区保持空态。
    </div>
    <div v-else-if="sourceEntries.length === 0" class="workspace-asset-rail__empty">
      当前时间线没有任何真实片段。资产中心、配音中心和字幕对齐接入后会出现在这里。
    </div>
    <ul v-else class="workspace-asset-rail__list">
      <li
        v-for="entry in sourceEntries"
        :key="entry.id"
        class="workspace-asset-rail__item"
        :class="{ 'workspace-asset-rail__item--active': selectedClip?.id === entry.id }"
      >
        <div>
          <strong>{{ entry.label }}</strong>
          <p>{{ entry.trackName }} · {{ sourceTypeLabel(entry.sourceType) }}</p>
        </div>
        <span :data-status="entry.status">
          {{ entry.status }}
        </span>
      </li>
    </ul>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { WorkspaceTimelineClipDto, WorkspaceTimelineDto } from "@/types/runtime";

const props = defineProps<{
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

const sourceEntries = computed(() =>
  props.timeline?.tracks.flatMap((track) =>
    track.clips.map((clip) => ({
      ...clip,
      trackName: track.name
    }))
  ) ?? []
);

const summaryTitle = computed(() => {
  if (!props.timeline) return "等待真实时间线";
  if (sourceEntries.value.length === 0) return "时间线仍为空";
  return `已接入 ${sourceEntries.value.length} 个真实片段`;
});

const summaryDescription = computed(() => {
  if (!props.timeline) return "创建草稿前不生成伪素材列表。";
  if (sourceEntries.value.length === 0) return "素材、配音、字幕都还没有落到时间线。";
  if (props.selectedClip) return `当前选中片段：${props.selectedClip.label}`;
  return "点击时间线片段后，这里会同步显示对应来源。";
});

function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "asset") return "资产中心";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音中心";
  if (sourceType === "subtitle_track") return "字幕对齐";
  if (sourceType === "manual") return "手动片段";
  return sourceType;
}
</script>

<style scoped>
.workspace-asset-rail {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 14px;
  padding: 18px;
}

.workspace-asset-rail__heading {
  align-items: center;
  display: flex;
  gap: 12px;
}

.workspace-asset-rail__heading p,
.workspace-asset-rail__summary p,
.workspace-asset-rail__item p,
.workspace-asset-rail__empty {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-asset-rail__summary {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 14%, transparent), transparent 60%),
    var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.workspace-asset-rail__summary small {
  color: var(--text-tertiary);
}

.workspace-asset-rail__empty {
  background: var(--surface-tertiary);
  border: 1px dashed var(--border-default);
  border-radius: 16px;
  padding: 16px;
}

.workspace-asset-rail__list {
  display: grid;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.workspace-asset-rail__item {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid transparent;
  border-radius: 14px;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 14px;
}

.workspace-asset-rail__item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.workspace-asset-rail__item span {
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.workspace-asset-rail__item span[data-status="ready"] {
  background: color-mix(in srgb, var(--color-success) 16%, transparent);
  color: var(--color-success);
}

.workspace-asset-rail__item span[data-status="blocked"] {
  background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  color: var(--color-warning);
}

.workspace-asset-rail__item span[data-status="error"],
.workspace-asset-rail__item span[data-status="missing_source"] {
  background: color-mix(in srgb, var(--color-danger) 16%, transparent);
  color: var(--color-danger);
}
</style>
