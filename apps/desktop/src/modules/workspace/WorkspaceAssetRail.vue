<template>
  <aside class="workspace-asset-rail" aria-label="工作台素材池">
    <div class="workspace-asset-rail__heading">
      <span class="material-symbols-outlined">inventory_2</span>
      <div>
        <strong>素材池</strong>
        <p>{{ sourceSummary }}</p>
      </div>
    </div>

    <div class="workspace-asset-rail__tabs" role="tablist" aria-label="素材来源">
      <button
        v-for="tab in sourceTabs"
        :key="tab.id"
        :aria-selected="activeTab === tab.id"
        :data-testid="tab.id === 'assets' ? 'workspace-asset-tab-assets' : undefined"
        role="tab"
        type="button"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="workspace-asset-rail__summary">
      <small>{{ activeSummaryLabel }}</small>
      <strong>{{ summaryTitle }}</strong>
      <p>{{ summaryDescription }}</p>
    </div>

    <template v-if="activeTab === 'assets'">
      <div class="workspace-asset-rail__actions">
        <button type="button" :disabled="assetStatus === 'loading'" @click="$emit('sync-assets')">
          <span class="material-symbols-outlined">sync</span>
          同步资产
        </button>
      </div>

      <div v-if="assetStatus === 'loading'" class="workspace-asset-rail__empty" data-state="loading">
        正在同步当前项目资产。
      </div>
      <div v-else-if="assetStatus === 'error'" class="workspace-asset-rail__empty" data-state="error">
        <strong>资产读取失败</strong>
        <p>{{ assetError?.message ?? "请稍后重试。" }}</p>
      </div>
      <div v-else-if="assetCards.length === 0" class="workspace-asset-rail__empty" data-state="empty">
        当前项目还没有可展示资产。
      </div>
      <div v-else class="workspace-asset-rail__list scroll-area">
        <article
          v-for="asset in assetCards"
          :key="asset.id"
          class="workspace-asset-card"
          :data-tone="asset.tone"
        >
          <div class="workspace-asset-card__thumbnail">
            <span class="material-symbols-outlined">{{ thumbnailIcon(asset.type) }}</span>
          </div>
          <div class="workspace-asset-card__body">
            <strong>{{ asset.name }}</strong>
            <p>{{ asset.summary }}</p>
            <span>{{ asset.status }}</span>
          </div>
          <button type="button" disabled>{{ asset.primaryAction }}</button>
        </article>
      </div>
    </template>

    <template v-else>
      <div v-if="sourceCards.length" class="workspace-asset-rail__sources">
        <article
          v-for="source in filteredSourceCards"
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
      <div v-else-if="filteredSourceEntries.length === 0" class="workspace-asset-rail__empty">
        当前来源还没有落到时间线的真实片段。
      </div>
      <div v-else class="workspace-asset-rail__list scroll-area">
        <transition-group name="source-list" tag="ul">
          <li
            v-for="entry in filteredSourceEntries"
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
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import {
  buildWorkspaceAssetCards,
  sourceTypeLabel,
  type WorkspaceAssetCard
} from "@/modules/workspace/workspaceAssetViewModel";
import type {
  AssetDto,
  RuntimeRequestErrorShape,
  WorkspaceAssemblyStateDto,
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto
} from "@/types/runtime";

type SourceTabId = "storyboard" | "voice_track" | "subtitle_track" | "assets";

const props = defineProps<{
  assemblyState: WorkspaceAssemblyStateDto | null;
  assetError: RuntimeRequestErrorShape | null;
  assetStatus: "idle" | "loading" | "ready" | "error";
  assets: AssetDto[];
  projectId: string;
  selectedClip: WorkspaceTimelineClipDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

defineEmits<{
  "sync-assets": [];
}>();

const activeTab = ref<SourceTabId>("assets");

const sourceTabs: Array<{ id: SourceTabId; label: string }> = [
  { id: "storyboard", label: "分镜" },
  { id: "voice_track", label: "配音" },
  { id: "subtitle_track", label: "字幕" },
  { id: "assets", label: "资产" }
];

const sourceEntries = computed(() =>
  props.timeline?.tracks.flatMap((track) =>
    track.clips.map((clip) => ({
      ...clip,
      trackName: track.name
    }))
  ) ?? []
);

const filteredSourceEntries = computed(() =>
  sourceEntries.value.filter((entry) => entry.sourceType === activeTab.value)
);

const sourceCards = computed(() => props.assemblyState?.sources ?? []);

const filteredSourceCards = computed(() => {
  const kind = sourceKindFromTab(activeTab.value);
  return sourceCards.value.filter((source) => source.kind === kind);
});

const assetCards = computed<WorkspaceAssetCard[]>(() =>
  buildWorkspaceAssetCards({
    projectId: props.projectId,
    assets: props.assets,
    timeline: props.timeline
  })
);

const sourceSummary = computed(() => {
  if (activeTab.value === "assets") return "当前项目资产中心素材。";
  if (!props.assemblyState) return "等待从脚本、分镜、配音和字幕汇入。";
  if (props.assemblyState.status === "ready") return "创作链路来源已接入时间线。";
  return props.assemblyState.issues.join(" ") || "部分来源仍需处理。";
});

const activeSummaryLabel = computed(() => (activeTab.value === "assets" ? "资产状态" : "汇入状态"));

const summaryTitle = computed(() => {
  if (activeTab.value === "assets") {
    if (props.assetStatus === "loading") return "正在同步资产";
    if (props.assetStatus === "error") return "资产同步失败";
    if (assetCards.value.length === 0) return "暂无项目资产";
    return `已接入 ${assetCards.value.length} 个资产`;
  }

  if (!props.timeline) return "等待真实时间线";
  if (filteredSourceEntries.value.length === 0) return "当前来源为空";
  return `已接入 ${filteredSourceEntries.value.length} 个真实片段`;
});

const summaryDescription = computed(() => {
  if (activeTab.value === "assets") {
    if (props.assetStatus === "error") return props.assetError?.message ?? "请重新同步资产。";
    if (assetCards.value.length === 0) return "无真实后端数据时不生成伪素材。";
    return "素材卡片当前只展示状态，加入或替换动作暂不触发。";
  }

  if (!props.timeline) return "创建草稿前不生成伪素材列表。";
  if (filteredSourceEntries.value.length === 0) return "该来源还没有落到时间线。";
  if (props.selectedClip) return `当前选中片段：${props.selectedClip.label}`;
  return "点击时间线片段后，这里会同步显示对应来源。";
});

function sourceKindFromTab(tab: SourceTabId): string {
  if (tab === "voice_track") return "voice";
  if (tab === "subtitle_track") return "subtitle";
  return tab;
}

function sourceKindLabel(kind: string): string {
  if (kind === "script") return "脚本";
  if (kind === "storyboard") return "分镜";
  if (kind === "voice") return "配音";
  if (kind === "subtitle") return "字幕";
  return kind;
}

function thumbnailIcon(type: string): string {
  if (type === "audio") return "graphic_eq";
  if (type === "image") return "image";
  return "movie";
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
  grid-template-rows: auto auto auto auto minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
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
.workspace-asset-rail__empty p,
.workspace-asset-rail__empty {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-asset-rail__tabs {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 4px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 4px;
}

.workspace-asset-rail__tabs button {
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  font: inherit;
  min-height: 30px;
}

.workspace-asset-rail__tabs button[aria-selected="true"] {
  background: var(--surface-primary);
  box-shadow: var(--shadow-sm);
  color: var(--text-primary);
  font-weight: 700;
}

.workspace-asset-rail__summary {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.workspace-asset-rail__summary small {
  color: var(--text-tertiary);
}

.workspace-asset-rail__actions button {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-primary);
  cursor: pointer;
  display: inline-flex;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
}

.workspace-asset-rail__actions button:disabled {
  cursor: wait;
  opacity: 0.7;
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
  display: grid;
  gap: 6px;
  padding: 16px;
}

.workspace-asset-rail__empty[data-state="error"] {
  border-color: color-mix(in srgb, var(--color-danger) 42%, var(--border-default));
}

.workspace-asset-rail__list {
  display: grid;
  gap: 10px;
  grid-auto-rows: max-content;
  list-style: none;
  margin: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 0;
}

.scroll-area {
  overflow-y: auto;
  scrollbar-color: var(--color-border-strong) transparent;
  scrollbar-width: thin;
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
  cursor: default;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 14px;
  transition: all var(--motion-fast) var(--ease-standard);
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

.workspace-asset-rail__item span,
.workspace-asset-card__body span {
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

.workspace-asset-card {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  padding: 12px;
}

.workspace-asset-card[data-tone="success"] {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--border-default));
}

.workspace-asset-card[data-tone="warning"] {
  border-color: color-mix(in srgb, var(--color-warning) 42%, var(--border-default));
}

.workspace-asset-card[data-tone="danger"] {
  border-color: color-mix(in srgb, var(--color-danger) 42%, var(--border-default));
}

.workspace-asset-card__thumbnail {
  align-items: center;
  aspect-ratio: 1;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 18%, transparent), transparent),
    var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  display: flex;
  justify-content: center;
}

.workspace-asset-card__body {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.workspace-asset-card__body strong,
.workspace-asset-card__body p {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-asset-card__body p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-asset-card__body span {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  color: var(--text-secondary);
  justify-self: start;
}

.workspace-asset-card button {
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  min-height: 32px;
  padding: 0 10px;
}

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
