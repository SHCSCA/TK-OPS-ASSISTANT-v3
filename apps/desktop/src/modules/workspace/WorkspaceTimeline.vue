<template>
  <section class="workspace-timeline" aria-label="项目时间线" :data-state="status">
    <header class="workspace-timeline__header">
      <div>
        <strong>时间线</strong>
        <p>{{ subtitle }}</p>
      </div>
      <div class="workspace-timeline__selection" :data-active="String(Boolean(selectedClip || selectedTrack))">
        <strong class="workspace-timeline__selection-label">{{ selectedSummary.label }}</strong>
        <span class="workspace-timeline__selection-meta">{{ selectedSummary.meta }}</span>
      </div>
    </header>

    <div v-if="status === 'loading'" class="workspace-timeline__empty">
      正在读取时间线轨道。
    </div>
    <div v-else-if="!timeline" class="workspace-timeline__empty">
      当前项目还没有时间线草稿。
    </div>
    <div v-else-if="rows.length === 0" class="workspace-timeline__empty">
      当前时间线还没有轨道，不补示例轨道。
    </div>
    <div v-else class="workspace-timeline__body">
      <div v-if="status === 'saving'" class="ai-flow-bar" />
      <div class="workspace-timeline__ruler" @click="handleTimelinePointer">
        <span
          v-for="marker in markers"
          :key="marker.label"
          class="workspace-timeline__tick"
          :style="{ left: marker.left }"
        >
          {{ marker.label }}
        </span>
      </div>
      <div
        class="workspace-timeline__playhead"
        data-testid="workspace-playhead"
        :style="{ left: `${playheadPercent}%` }"
      >
        <span>{{ playheadLabel }}</span>
      </div>

      <div class="workspace-timeline__tracks scroll-area">
        <transition-group name="track-list">
          <article
            v-for="row in rows"
            :key="row.id"
            class="workspace-track"
            :class="[
              `workspace-track--${row.heightClass}`,
              `workspace-track--${row.visualClass}`,
              { 'workspace-track--selected': selectedTrackId === row.id }
            ]"
          >
            <button class="workspace-track__label" type="button" @click="$emit('select-track', row.id)">
              <span class="material-symbols-outlined">{{ trackIcon(row.kind) }}</span>
              <div>
                <strong>{{ row.name }}</strong>
                <small>{{ trackMeta(row) }}</small>
              </div>
            </button>

            <div class="workspace-track__lane" @click="handleTimelinePointer">
              <transition-group name="clip-list">
                <button
                  v-for="clipView in row.clips"
                  :key="clipView.id"
                  class="workspace-clip"
                  :class="[
                    `workspace-clip--${clipView.joinClass}`,
                    { 'workspace-clip--selected': selectedClipId === clipView.id }
                  ]"
                  :data-status="clipView.clip.status"
                  type="button"
                  :style="clipStyle(clipView)"
                  @click.stop="$emit('select-clip', { clipId: clipView.id, trackId: row.id })"
                >
                  <span
                    v-if="clipView.id === selectedClipId"
                    aria-label="左侧裁剪 0.5 秒"
                    class="workspace-timeline__trim-handle workspace-timeline__trim-handle--left"
                    data-testid="workspace-trim-left"
                    role="button"
                    tabindex="0"
                    title="左侧收短 0.5 秒"
                    @click.stop="emitTrim(clipView.id, 'left', 500)"
                    @keydown.enter.stop.prevent="emitTrim(clipView.id, 'left', 500)"
                    @keydown.space.stop.prevent="emitTrim(clipView.id, 'left', 500)"
                  />
                  <span
                    v-if="clipView.id === selectedClipId"
                    aria-label="右侧裁剪 0.5 秒"
                    class="workspace-timeline__trim-handle workspace-timeline__trim-handle--right"
                    data-testid="workspace-trim-right"
                    role="button"
                    tabindex="0"
                    title="右侧收短 0.5 秒"
                    @click.stop="emitTrim(clipView.id, 'right', -500)"
                    @keydown.enter.stop.prevent="emitTrim(clipView.id, 'right', -500)"
                    @keydown.space.stop.prevent="emitTrim(clipView.id, 'right', -500)"
                  />
                  <div v-if="row.visualClass === 'video'" class="workspace-timeline__thumbnail-strip" aria-hidden="true">
                    <span v-for="index in 5" :key="index" />
                  </div>
                  <div
                    v-else-if="row.visualClass === 'voice' || row.visualClass === 'bgm'"
                    class="workspace-timeline__waveform"
                    aria-hidden="true"
                  >
                    <span v-for="index in 14" :key="index" />
                  </div>
                  <div v-else class="workspace-timeline__subtitle-block">
                    {{ subtitleText(clipView.clip) }}
                  </div>
                  <strong>{{ clipLabel(clipView.clip) }}</strong>
                  <small>{{ clipSubtitle(clipView.clip) }}</small>
                </button>
              </transition-group>
              <span v-if="row.clips.length === 0" class="workspace-track__empty">当前轨道暂无片段</span>
            </div>
          </article>
        </transition-group>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineTrackKind
} from "@/types/runtime";
import {
  buildTimelineRows,
  cleanWorkspaceText,
  computePlayheadPercent,
  formatWorkspaceClipRange,
  formatWorkspaceTime,
  type TimelineClipView,
  type TimelineRowView,
  workspaceSourceTypeLabel,
  workspaceStatusLabel,
  workspaceTrackMetaLabel
} from "./workspaceTimelineViewModel";

const props = defineProps<{
  selectedClipId: string | null;
  selectedTrackId: string | null;
  playheadMs: number;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
  tracks: WorkspaceTimelineTrackDto[];
}>();

const emit = defineEmits<{
  playhead: [positionMs: number];
  "select-clip": [payload: { clipId: string; trackId: string }];
  "select-track": [trackId: string];
  trim: [payload: { clipId: string; edge: "left" | "right"; deltaMs: number }];
}>();

const durationMs = computed(() => {
  const clips = props.timeline?.tracks.flatMap((track) => track.clips) ?? [];
  const clipEnd = clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0);
  const declaredDuration = Math.max(0, (props.timeline?.durationSeconds ?? 0) * 1000);
  return Math.max(declaredDuration, clipEnd, 1000);
});

const markers = computed(() => {
  const count = 6;
  return Array.from({ length: count + 1 }, (_, index) => {
    const ratio = index / count;
    return {
      label: formatWorkspaceTime(durationMs.value * ratio),
      left: `${ratio * 100}%`
    };
  });
});

const rows = computed(() => buildTimelineRows(props.tracks, durationMs.value));

const selectedClip = computed(() => {
  if (!props.selectedClipId) return null;

  for (const row of rows.value) {
    const clipView = row.clips.find((clip) => clip.id === props.selectedClipId);
    if (clipView) return clipView.clip;
  }

  return null;
});

const selectedTrack = computed(() => {
  if (!props.selectedTrackId) return null;
  return rows.value.find((row) => row.id === props.selectedTrackId) ?? null;
});

const selectedClipTrackName = computed(() => {
  if (!selectedClip.value) return "";
  return rows.value.find((row) => row.clips.some((clipView) => clipView.id === selectedClip.value?.id))?.name ?? "未知轨道";
});

const playheadPercent = computed(() => computePlayheadPercent(props.playheadMs, durationMs.value));
const playheadLabel = computed(() => formatWorkspaceTime(props.playheadMs));

const subtitle = computed(() => {
  if (!props.timeline) return "等待创建时间线草稿";
  return `${props.timeline.name} · ${rows.value.length} 条轨道 · ${formatWorkspaceTime(durationMs.value)}`;
});

const selectedSummary = computed(() => {
  if (selectedClip.value) {
    return {
      label: clipLabel(selectedClip.value),
      meta: `${selectedClipTrackName.value} · ${workspaceStatusLabel(selectedClip.value.status)} · ${formatWorkspaceClipRange(selectedClip.value.startMs, selectedClip.value.durationMs)}`
    };
  }

  if (selectedTrack.value) {
    return {
      label: selectedTrack.value.name,
      meta: `${trackMeta(selectedTrack.value)} · ${selectedTrack.value.clips.length} 个片段`
    };
  }

  return {
    label: "未选择片段",
    meta: "点击时间线片段或素材池来源查看详情"
  };
});

function trackIcon(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "graphic_eq";
  if (kind === "subtitle") return "subtitles";
  return "movie";
}

function trackMeta(row: TimelineRowView): string {
  return workspaceTrackMetaLabel({
    id: row.id,
    kind: row.kind,
    name: row.name,
    clipCount: row.clips.length
  });
}

function clipSubtitle(clip: WorkspaceTimelineClipDto): string {
  const segmentId = clip.metadata?.segmentId ? `${clip.metadata.segmentId} · ` : "";
  const status = clip.status === "ready" ? "" : `${workspaceStatusLabel(clip.status)} · `;
  return `${segmentId}${workspaceSourceTypeLabel(clip.sourceType)} · ${status}${formatWorkspaceClipRange(clip.startMs, clip.durationMs)}`;
}

function clipStyle(clipView: TimelineClipView): Record<string, string> {
  return {
    left: `${clipView.leftPercent}%`,
    width: `${clipView.widthPercent}%`
  };
}

function subtitleText(clip: WorkspaceTimelineClipDto): string {
  return cleanWorkspaceText(clip.metadata?.text, clip.label);
}

function clipLabel(clip: WorkspaceTimelineClipDto): string {
  return cleanWorkspaceText(clip.label, workspaceSourceTypeLabel(clip.sourceType));
}

function handleTimelinePointer(event: MouseEvent): void {
  const target = event.currentTarget as HTMLElement | null;
  if (!target) return;

  const rect = target.getBoundingClientRect();
  if (rect.width <= 0) return;

  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  emit("playhead", Math.round(durationMs.value * ratio));
}

function emitTrim(clipId: string, edge: "left" | "right", deltaMs: number): void {
  emit("trim", { clipId, edge, deltaMs });
}
</script>

<style scoped>
.workspace-timeline {
  min-height: 0;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(17, 24, 39, 0.96), rgba(3, 7, 18, 0.98)),
    var(--surface-secondary);
  border: 1px solid color-mix(in srgb, var(--border-strong) 58%, transparent);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  color: #eef4ff;
}

.workspace-timeline__header,
.workspace-track,
.workspace-track__label {
  display: flex;
  gap: 14px;
}

.workspace-timeline__header,
.workspace-track {
  justify-content: space-between;
}

.workspace-timeline__header {
  align-items: center;
  min-height: 34px;
  padding: 0 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.86);
}

.workspace-timeline__header > div {
  min-width: 0;
}

.workspace-timeline__header p,
.workspace-track__label small,
.workspace-track__empty,
.workspace-timeline__empty {
  color: rgba(203, 213, 225, 0.72);
  margin: 0;
}

.workspace-timeline__selection {
  display: grid;
  justify-items: end;
  gap: 2px;
  min-width: 0;
  max-width: min(420px, 42vw);
  color: rgba(226, 232, 240, 0.84);
}

.workspace-timeline__selection-label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(248, 250, 252, 0.94);
  font-size: 12px;
}

.workspace-timeline__selection-meta {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(203, 213, 225, 0.68);
  font-size: 11px;
}

.workspace-timeline__selection[data-active="true"] .workspace-timeline__selection-label {
  color: #fde68a;
}

.workspace-timeline__empty {
  display: flex;
  min-height: 150px;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.7);
  border: 1px dashed rgba(148, 163, 184, 0.22);
  padding: 18px;
  text-align: center;
}

.workspace-timeline__body {
  display: grid;
  grid-template-rows: 28px minmax(0, 1fr);
  min-height: 0;
  position: relative;
}

.ai-flow-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  animation: ai-flow 2.4s linear infinite;
  z-index: 10;
}

.workspace-timeline__ruler {
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  background:
    linear-gradient(to right, rgba(148, 163, 184, 0.16) 1px, transparent 1px),
    rgba(2, 6, 23, 0.72);
  background-size: 80px 100%;
  min-height: 28px;
  position: relative;
}

.workspace-timeline__tick {
  color: rgba(148, 163, 184, 0.9);
  font-size: 11px;
  position: absolute;
  top: 7px;
  transform: translateX(-50%);
}

.workspace-timeline__playhead {
  bottom: 0;
  position: absolute;
  top: 0;
  width: 1px;
  background: #facc15;
  box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.35), 0 0 18px rgba(250, 204, 21, 0.4);
  transform: translateX(-0.5px);
  z-index: 8;
}

.workspace-timeline__playhead::before {
  content: "";
  position: absolute;
  top: 26px;
  left: -5px;
  width: 11px;
  height: 11px;
  background: #facc15;
  clip-path: polygon(50% 100%, 0 0, 100% 0);
}

.workspace-timeline__playhead span {
  position: absolute;
  top: 6px;
  left: 8px;
  padding: 2px 6px;
  border: 1px solid rgba(250, 204, 21, 0.4);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.92);
  color: #fde68a;
  font-size: 11px;
  white-space: nowrap;
}

.workspace-timeline__tracks {
  display: grid;
  gap: 0;
  height: 100%;
  min-height: 0;
  overflow: auto;
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

.workspace-track {
  align-items: stretch;
  display: grid;
  grid-template-columns: 144px minmax(0, 1fr);
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.46);
  padding: 0;
}

.workspace-track--tall {
  min-height: 64px;
}

.workspace-track--medium {
  min-height: 46px;
}

.workspace-track--compact {
  min-height: 34px;
}

.workspace-track--selected {
  background: color-mix(in srgb, var(--brand-primary) 14%, rgba(15, 23, 42, 0.72));
  box-shadow: inset 3px 0 0 var(--brand-primary);
}

.workspace-track--video .workspace-track__label .material-symbols-outlined {
  color: #38bdf8;
}

.workspace-track--voice .workspace-track__label .material-symbols-outlined {
  color: #22c55e;
}

.workspace-track--bgm .workspace-track__label .material-symbols-outlined {
  color: #a78bfa;
}

.workspace-track--subtitle .workspace-track__label .material-symbols-outlined {
  color: #fb7185;
}

.workspace-track__label {
  align-items: center;
  background: rgba(2, 6, 23, 0.42);
  border: 0;
  border-right: 1px solid rgba(148, 163, 184, 0.16);
  color: inherit;
  min-width: 0;
  flex-shrink: 0;
  padding: 8px 10px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-track__label .material-symbols-outlined {
  flex: 0 0 auto;
  font-size: 21px;
}

.workspace-track__lane {
  background:
    linear-gradient(to right, rgba(148, 163, 184, 0.16) 1px, transparent 1px),
    linear-gradient(180deg, rgba(15, 23, 42, 0.18), rgba(2, 6, 23, 0.32));
  background-size: 80px 100%, 100% 100%;
  min-height: 100%;
  overflow: hidden;
  position: relative;
}

.workspace-clip {
  align-content: start;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  color: #f8fafc;
  display: grid;
  gap: 5px;
  min-width: 0;
  overflow: hidden;
  padding: 6px 9px;
  position: absolute;
  top: 5px;
  bottom: 5px;
  transition: all var(--motion-fast) var(--ease-standard);
  cursor: pointer;
}

.workspace-timeline__trim-handle {
  background: rgba(250, 204, 21, 0.88);
  border: 1px solid rgba(254, 243, 199, 0.86);
  border-radius: 99px;
  bottom: 7px;
  box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.14);
  cursor: ew-resize;
  position: absolute;
  top: 7px;
  width: 7px;
  z-index: 2;
}

.workspace-timeline__trim-handle--left {
  left: 4px;
}

.workspace-timeline__trim-handle--right {
  right: 4px;
}

.workspace-track--tall .workspace-clip {
  grid-template-rows: minmax(24px, 1fr) auto auto;
}

.workspace-track--medium .workspace-clip {
  grid-template-rows: minmax(16px, 1fr) auto;
}

.workspace-track--compact .workspace-clip {
  grid-template-rows: minmax(18px, 1fr) auto;
  padding: 6px 10px;
}

.workspace-clip:active {
  transform: scale(0.98);
}

.workspace-clip--selected {
  border-color: rgba(250, 204, 21, 0.72);
  box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.36), 0 0 18px rgba(250, 204, 21, 0.22);
}

.workspace-clip--start {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.workspace-clip--middle {
  border-radius: 0;
}

.workspace-clip--end {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.workspace-track--video .workspace-clip {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.34), rgba(15, 23, 42, 0.94));
}

.workspace-track--voice .workspace-clip {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.28), rgba(15, 23, 42, 0.94));
}

.workspace-track--bgm .workspace-clip {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.32), rgba(15, 23, 42, 0.94));
}

.workspace-track--subtitle .workspace-clip {
  background: linear-gradient(135deg, rgba(244, 63, 94, 0.28), rgba(15, 23, 42, 0.94));
}

.workspace-timeline__thumbnail-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(18px, 1fr));
  gap: 3px;
  min-height: 20px;
}

.workspace-timeline__thumbnail-strip span {
  border: 1px solid rgba(125, 211, 252, 0.14);
  border-radius: 5px;
  background:
    radial-gradient(circle at 30% 22%, rgba(255, 255, 255, 0.22), transparent 24px),
    linear-gradient(135deg, rgba(56, 189, 248, 0.34), rgba(14, 116, 144, 0.1) 46%, rgba(15, 23, 42, 0.86));
}

.workspace-timeline__waveform {
  display: flex;
  min-height: 16px;
  align-items: center;
  gap: 3px;
}

.workspace-timeline__waveform span {
  flex: 1 1 0;
  min-width: 2px;
  height: 12px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.74;
}

.workspace-timeline__waveform span:nth-child(3n + 1) {
  height: 16px;
}

.workspace-timeline__waveform span:nth-child(4n + 2) {
  height: 12px;
}

.workspace-timeline__waveform span:nth-child(5n) {
  height: 8px;
}

.workspace-track--voice .workspace-timeline__waveform {
  color: #86efac;
}

.workspace-track--bgm .workspace-timeline__waveform {
  color: #c4b5fd;
}

.workspace-timeline__subtitle-block {
  display: flex;
  min-height: 20px;
  align-items: center;
  overflow: hidden;
  color: #fecdd3;
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-list-move,
.track-list-enter-active,
.track-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.track-list-enter-from,
.track-list-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.clip-list-move,
.clip-list-enter-active,
.clip-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.clip-list-enter-from,
.clip-list-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.workspace-clip[data-status="blocked"] {
  border-color: color-mix(in srgb, var(--color-warning) 44%, rgba(148, 163, 184, 0.24));
}

.workspace-clip[data-status="error"],
.workspace-clip[data-status="missing_source"] {
  border-color: color-mix(in srgb, var(--color-danger) 52%, rgba(148, 163, 184, 0.24));
}

.workspace-clip strong,
.workspace-clip small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-clip strong {
  color: #f8fafc;
  font-size: 12px;
}

.workspace-clip small {
  color: rgba(226, 232, 240, 0.72);
  font-size: 11px;
}

.workspace-track__empty {
  left: 16px;
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
}

@media (max-width: 960px) {
  .workspace-track {
    grid-template-columns: 112px minmax(0, 1fr);
  }

  .workspace-track__label {
    padding: 10px;
  }

  .workspace-track__label small {
    white-space: normal;
  }

  .workspace-timeline__playhead span {
    display: none;
  }
}
</style>
