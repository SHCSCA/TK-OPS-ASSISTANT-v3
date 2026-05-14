<template>
  <aside class="workspace-asset-rail" aria-label="工作台素材池">
    <div class="workspace-asset-rail__heading">
      <span class="material-symbols-outlined">inventory_2</span>
      <div>
        <strong>素材池</strong>
        <p>{{ sourceSummary }}</p>
      </div>
    </div>

    <div class="workspace-asset-rail__summary">
      <small>汇入状态</small>
      <strong>{{ summaryTitle }}</strong>
      <p>{{ summaryDescription }}</p>
    </div>

    <div v-if="sourceCards.length" class="workspace-asset-rail__sources">
      <article
        v-for="source in sourceCards"
        :key="source.kind"
        class="workspace-asset-rail__source"
        :data-status="source.status"
      >
        <span>{{ sourceKindLabel(source.kind) }}</span>
        <strong>{{ source.segmentCount }} 段</strong>
      </article>
    </div>

    <div v-if="!timeline" class="workspace-asset-rail__empty">
      还没有时间线草稿，素材区保持空态。
    </div>
    <div v-else-if="sourceEntries.length === 0" class="workspace-asset-rail__empty">
      当前时间线没有任何真实片段。资产中心、配音中心和字幕对齐接入后会出现在这里。
    </div>
    <div v-else class="workspace-asset-rail__list scroll-area">
      <transition-group name="source-list" tag="ul">
        <li
          v-for="entry in sourceEntries"
          :key="entry.id"
          class="workspace-asset-rail__item"
          :class="{ 'workspace-asset-rail__item--active': selectedClip?.id === entry.id }"
        >
          <div>
            <strong>{{ entry.label }}</strong>
            <p>{{ entry.trackName }} · {{ sourceTypeLabel(entry.sourceType) }} · {{ trackPolicy(entry.trackId) }}</p>
          </div>
          <span :data-status="entry.status">
            {{ entry.status }}
          </span>
        </li>
      </transition-group>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  WorkspaceAssemblyStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto
} from "@/types/runtime";

const props = defineProps<{
  assemblyState: WorkspaceAssemblyStateDto | null;
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

const sourceCards = computed(() => props.assemblyState?.sources ?? []);

const sourceSummary = computed(() => {
  if (!props.assemblyState) return "等待从脚本、分镜、配音和字幕汇入。";
  if (props.assemblyState.status === "ready") return "创作链路来源已接入时间线。";
  return props.assemblyState.issues.join(" ") || "部分来源仍需处理。";
});

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

function sourceKindLabel(kind: string): string {
  if (kind === "script") return "脚本";
  if (kind === "storyboard") return "分镜";
  if (kind === "voice") return "配音";
  if (kind === "subtitle") return "字幕";
  return kind;
}

function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "storyboard") return "分镜规划";
  if (sourceType === "asset") return "资产中心";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音中心";
  if (sourceType === "subtitle_track") return "字幕对齐";
  if (sourceType === "manual") return "手动片段";
  return sourceType;
}

function trackPolicy(trackId: string): string {
  return trackId.startsWith("managed-") ? "受管轨道" : "手动轨道";
}
</script>

<style scoped>
.workspace-asset-rail {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
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
    var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.workspace-asset-rail__summary small {
  color: var(--text-tertiary);
}

.workspace-asset-rail__sources {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workspace-asset-rail__source {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 4px;
  padding: 10px;
}

.workspace-asset-rail__source span {
  color: var(--text-tertiary);
  font-size: 12px;
}

.workspace-asset-rail__source[data-status="missing"] {
  border-color: color-mix(in srgb, var(--color-warning) 40%, var(--border-default));
}

.workspace-asset-rail__empty {
  background: var(--surface-tertiary);
  border: 1px dashed var(--border-default);
  border-radius: 8px;
  padding: 16px;
}

.workspace-asset-rail__list {
  display: grid;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.scroll-area {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.scroll-area::-webkit-scrollbar {
  width: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.workspace-asset-rail__item {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid transparent;
  border-radius: 8px;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 14px;
  transition: all var(--motion-fast) var(--ease-standard);
  cursor: default;
}

.workspace-asset-rail__item:hover {
  background: var(--color-bg-hover);
}

.workspace-asset-rail__item:active {
  transform: scale(0.98);
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

/* Transitions */
.source-list-move,
.source-list-enter-active,
.source-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.source-list-enter-from,
.source-list-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>
