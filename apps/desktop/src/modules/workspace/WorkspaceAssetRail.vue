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
        :data-source-tab="tab.id"
        :data-testid="tab.testId"
        role="tab"
        type="button"
        @click.stop="selectSourceTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="workspace-asset-rail__summary">
      <span>{{ activeSummaryLabel }}</span>
      <strong>{{ summaryTitle }}</strong>
      <small :title="summaryDescription">{{ summaryDescription }}</small>
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
          </div>
          <div class="workspace-asset-card__meta">
            <div class="workspace-asset-card__state">
              <span class="workspace-asset-card__status">{{ asset.status }}</span>
              <small v-if="assetUnavailableReason(asset)">{{ assetUnavailableReason(asset) }}</small>
            </div>
            <div class="workspace-asset-card__actions">
              <button
                type="button"
                :disabled="!canInsertAsset(asset)"
                @click="emit('asset-insert', asset.id)"
              >
                加入时间线
              </button>
              <button
                type="button"
                :disabled="!canReplaceAsset(asset)"
                @click="emit('asset-replace', asset.id)"
              >
                替换片段
              </button>
            </div>
          </div>
        </article>
      </div>
    </template>

    <template v-else>
      <div v-if="!timeline" class="workspace-asset-rail__empty">
        还没有时间线草稿，素材区保持空态。
      </div>
      <div v-else-if="filteredSourceEntries.length === 0" class="workspace-asset-rail__empty">
        当前来源还没有落到时间线的真实片段。
      </div>
      <div v-else class="workspace-asset-rail__list scroll-area">
        <ul class="workspace-asset-rail__source-list">
          <li
            v-for="entry in filteredSourceEntries"
            :key="entry.id"
            class="workspace-asset-rail__item"
            :class="{ 'workspace-asset-rail__item--active': selectedClip?.id === entry.id }"
          >
            <button
              class="workspace-asset-rail__item-card"
              type="button"
              @click="$emit('select-source-clip', { clipId: entry.id, trackId: entry.trackId })"
            >
              <div class="workspace-asset-rail__item-main">
                <div class="workspace-asset-rail__item-head">
                  <strong>{{ sourceEntryLabel(entry) }}</strong>
                  <span class="workspace-asset-rail__item-status" :data-status="entry.status">
                    {{ workspaceStatusLabel(entry.status) }}
                  </span>
                </div>
                <span class="workspace-asset-rail__item-time">{{ sourceEntryTime(entry) }}</span>
                <p>{{ entry.trackName }} · {{ sourceTypeLabel(entry.sourceType) }} · {{ trackPolicy(entry.trackId) }}</p>
              </div>
            </button>
          </li>
        </ul>
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
import {
  cleanWorkspaceText,
  formatWorkspaceClipRange,
  workspaceStatusLabel
} from "@/modules/workspace/workspaceTimelineViewModel";
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

const emit = defineEmits<{
  "asset-insert": [assetId: string];
  "asset-replace": [assetId: string];
  "sync-assets": [];
  "select-source-clip": [payload: { clipId: string; trackId: string }];
}>();

const activeTab = ref<SourceTabId>("assets");

const sourceTabs: Array<{ id: SourceTabId; label: string; testId: string }> = [
  { id: "storyboard", label: "分镜", testId: "workspace-asset-tab-storyboard" },
  { id: "voice_track", label: "配音", testId: "workspace-asset-tab-voice_track" },
  { id: "subtitle_track", label: "字幕", testId: "workspace-asset-tab-subtitle_track" },
  { id: "assets", label: "资产", testId: "workspace-asset-tab-assets" }
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
    return "可加入时间线，也可按轨道兼容性替换选中片段。";
  }

  if (!props.timeline) return "创建草稿前不生成伪素材列表。";
  if (filteredSourceEntries.value.length === 0) return "该来源还没有落到时间线。";
  if (props.selectedClip) return `当前选中片段：${cleanWorkspaceText(props.selectedClip.label, "待确认片段")}`;
  return "点击时间线片段后，这里会同步显示对应来源。";
});

function thumbnailIcon(type: string): string {
  if (type === "audio") return "graphic_eq";
  if (type === "image") return "image";
  return "movie";
}

function canInsertAsset(asset: WorkspaceAssetCard): boolean {
  return isSupportedAssetType(asset) && isAssetAvailable(asset) && Boolean(props.timeline);
}

function canReplaceAsset(asset: WorkspaceAssetCard): boolean {
  return isAssetAvailable(asset) && isAssetCompatibleWithSelectedTrack(asset);
}

function assetUnavailableReason(asset: WorkspaceAssetCard): string {
  if (isAssetAvailable(asset)) return "";
  return asset.asset.availability.errorMessage || neutralUnavailableReason(asset.asset.availability.status);
}

function isAssetAvailable(asset: WorkspaceAssetCard): boolean {
  return ["available", "ready"].includes(asset.asset.availability.status);
}

function isSupportedAssetType(asset: WorkspaceAssetCard): boolean {
  return ["video", "image", "audio"].includes(asset.type);
}

function isAssetCompatibleWithSelectedTrack(asset: WorkspaceAssetCard): boolean {
  if (!props.selectedClip || !props.timeline) return false;
  const selectedTrack = props.timeline.tracks.find((track) => track.id === props.selectedClip?.trackId);
  if (!selectedTrack) return false;
  if (asset.type === "video" || asset.type === "image") return selectedTrack.kind === "video";
  if (asset.type === "audio") return selectedTrack.kind === "audio";
  return false;
}

function neutralUnavailableReason(status: string): string {
  if (["missing", "missing_source", "missing_file"].includes(status)) return "资产当前不可用，请重新定位或重新导入。";
  if (status === "needs_transcode") return "资产需要处理后才能使用。";
  return "资产当前不可用，请在资产中心处理后再使用。";
}

function trackPolicy(trackId: string): string {
  return trackId.startsWith("managed-") ? "受管轨道" : "手动轨道";
}

function sourceEntryLabel(entry: WorkspaceTimelineClipDto): string {
  return cleanWorkspaceText(entry.label, sourceTypeLabel(entry.sourceType));
}

function sourceEntryTime(entry: WorkspaceTimelineClipDto): string {
  return formatWorkspaceClipRange(entry.startMs, entry.durationMs);
}

function selectSourceTab(tabId: SourceTabId): void {
  activeTab.value = tabId;
}
</script>

<style scoped>
.workspace-asset-rail {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 10px;
  grid-template-rows: auto auto auto auto minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  padding: 14px;
}

.workspace-asset-rail__heading {
  align-items: center;
  display: flex;
  gap: 12px;
}

.workspace-asset-rail__heading p,
.workspace-asset-rail__item-main p,
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
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 6px 10px;
  grid-template-columns: auto minmax(0, 1fr);
  padding: 8px 10px;
}

.workspace-asset-rail__summary span,
.workspace-asset-rail__summary small {
  color: var(--text-tertiary);
  font-size: 12px;
}

.workspace-asset-rail__summary strong,
.workspace-asset-rail__summary small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-asset-rail__summary small {
  grid-column: 1 / -1;
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
  margin: 0;
  min-height: 0;
  overflow-y: auto;
  padding: 0;
}

.workspace-asset-rail__source-list {
  display: grid;
  gap: 8px;
  grid-auto-rows: max-content;
  list-style: none;
  margin: 0;
  min-width: 0;
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
  list-style: none;
  min-width: 0;
}

.workspace-asset-rail__item-card {
  align-items: start;
  appearance: none;
  background: var(--surface-tertiary);
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-primary);
  cursor: pointer;
  display: grid;
  gap: 8px;
  grid-template-columns: minmax(0, 1fr);
  padding: 10px 12px;
  text-align: left;
  transition: all var(--motion-fast) var(--ease-standard);
  width: 100%;
}

.workspace-asset-rail__item-card:hover,
.workspace-asset-rail__item-card:focus-visible {
  background: var(--color-bg-hover);
  outline: none;
}

.workspace-asset-rail__item-card:active {
  transform: scale(0.98);
}

.workspace-asset-rail__item--active .workspace-asset-rail__item-card {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.workspace-asset-rail__item-main {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.workspace-asset-rail__item-head {
  align-items: start;
  display: grid;
  gap: 8px;
  grid-template-columns: minmax(0, 1fr) auto;
  min-width: 0;
}

.workspace-asset-rail__item-main strong,
.workspace-asset-rail__item-time,
.workspace-asset-rail__item-main p {
  min-width: 0;
  overflow: hidden;
}

.workspace-asset-rail__item-main strong {
  display: -webkit-box;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.workspace-asset-rail__item-time {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-asset-rail__item-main p {
  color: var(--text-secondary);
  display: -webkit-box;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.workspace-asset-rail__item-status {
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.workspace-asset-rail__item-status {
  align-self: start;
  color: var(--text-secondary);
  white-space: nowrap;
}

.workspace-asset-rail__item-status[data-status="ready"] {
  background: color-mix(in srgb, var(--color-success) 16%, transparent);
  color: var(--color-success);
}

.workspace-asset-rail__item-status[data-status="blocked"] {
  background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  color: var(--color-warning);
}

.workspace-asset-rail__item-status[data-status="error"],
.workspace-asset-rail__item-status[data-status="missing_source"] {
  background: color-mix(in srgb, var(--color-danger) 16%, transparent);
  color: var(--color-danger);
}

.workspace-asset-card {
  align-items: start;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 10px 12px;
  grid-template-columns: 44px minmax(0, 1fr);
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
  min-width: 0;
}

.workspace-asset-card__body {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.workspace-asset-card__body strong,
.workspace-asset-card__body p {
  display: -webkit-box;
  line-height: 1.35;
  overflow: hidden;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.workspace-asset-card__body p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-asset-card__meta {
  align-items: start;
  display: flex;
  gap: 8px;
  grid-column: 1 / -1;
  justify-content: space-between;
  min-width: 0;
}

.workspace-asset-card__state {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.workspace-asset-card__state small {
  color: var(--text-secondary);
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.workspace-asset-card__status {
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
  border-radius: 999px;
  color: var(--text-secondary);
  flex: 0 0 auto;
  font-size: 12px;
  padding: 4px 10px;
  white-space: nowrap;
}

.workspace-asset-card__actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.workspace-asset-card button {
  background: var(--surface-primary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-primary);
  flex: 0 0 auto;
  min-height: 32px;
  padding: 0 10px;
  white-space: nowrap;
}

.workspace-asset-card button:disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
  opacity: 0.62;
}

</style>
