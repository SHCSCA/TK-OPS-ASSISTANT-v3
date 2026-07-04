<template>
  <section
    class="workspace-timeline"
    data-testid="workspace-timeline"
    aria-label="项目时间线"
    :data-state="status"
    :data-zoom-percent="safeZoomPercent"
  >
    <header class="workspace-timeline__header">
      <div>
        <strong>时间线</strong>
        <p>{{ subtitle }}</p>
      </div>
      <div
        v-if="syncSummary.visible"
        class="workspace-timeline__sync-summary"
        :data-sync="syncSummary.status"
        data-testid="workspace-timeline-sync-summary"
      >
        <span class="material-symbols-outlined">{{ syncSummary.icon }}</span>
        <div>
          <strong>{{ syncSummary.label }}</strong>
          <small>{{ syncSummary.meta }}</small>
        </div>
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
      <div class="workspace-timeline__viewport">
        <div
          class="workspace-timeline__content"
          data-testid="workspace-timeline-content"
          :style="timelineContentStyle"
        >
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
          <div class="workspace-timeline__playhead-layer">
            <div
              v-if="syncSummary.visible"
              class="workspace-timeline__sync-end"
              data-testid="workspace-sync-end"
              :style="{ left: `${syncTargetPercent}%` }"
            >
              <span>AI 统一结束</span>
            </div>
            <div
              class="workspace-timeline__playhead"
              data-testid="workspace-playhead"
              :style="{ left: `${playheadPercent}%` }"
            >
              <span>{{ playheadLabel }}</span>
            </div>
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
                    <small
                      v-if="row.isManagedAITrack"
                      class="workspace-track__sync-badge"
                      :data-sync="row.syncStatus"
                    >
                      {{ row.syncLabel }}
                    </small>
                  </div>
                </button>

                <div class="workspace-track__lane" @click="handleTimelinePointer">
                  <span
                    v-if="row.isManagedAITrack"
                    class="workspace-track__sync-target"
                    :data-sync="row.syncStatus"
                    :style="{ width: `${row.syncTargetPercent}%` }"
                  >
                    <span>AI 统一目标</span>
                  </span>
                  <span
                    v-if="row.isManagedAITrack"
                    class="workspace-track__sync-span"
                    :data-sync="row.syncStatus"
                    :style="{ width: `${row.syncEndPercent}%` }"
                  >
                    <span>{{ row.syncLabel }}</span>
                  </span>
                  <span
                    v-if="row.isManagedAITrack && row.syncGapWidthPercent > 0"
                    class="workspace-track__sync-gap"
                    :data-sync="row.syncStatus"
                    :style="{ left: `${row.syncGapLeftPercent}%`, width: `${row.syncGapWidthPercent}%` }"
                  >
                    <span>{{ row.syncLabel }}</span>
                  </span>
                  <transition-group name="clip-list">
                    <button
                      v-for="clipView in row.clips"
                      :key="clipView.id"
                      class="workspace-clip"
                      :class="[
                        `workspace-clip--${clipView.joinClass}`,
                        { 'workspace-clip--selected': selectedClipId === clipView.id }
                      ]"
                      :data-clip-id="clipView.id"
                      :data-status="clipView.clip.status"
                      type="button"
                      :style="clipStyle(clipView)"
                      @click.stop="$emit('select-clip', { clipId: clipView.id, trackId: row.id })"
                      @pointerdown.stop="handleMovePointerDown(clipView.clip, $event)"
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
                        @pointerdown.stop="handleTrimPointerDown(clipView.clip, 'left', $event)"
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
                        @pointerdown.stop="handleTrimPointerDown(clipView.clip, 'right', $event)"
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
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { EditingWorkspaceStatus } from "@/stores/editing-workspace";
import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto,
  WorkspaceTimelineTrackKind
} from "@/types/runtime";
import {
  useWorkspaceTimelineDrag,
  type WorkspaceTimelineDragPreview,
  type WorkspaceTimelineMovePreview,
  type WorkspaceTimelineTrimEdge,
  type WorkspaceTimelineTrimPreview
} from "./useWorkspaceTimelineDrag";
import { buildSnapCandidates } from "./workspaceTimelineSnap";
import {
  buildTimelineRows,
  cleanWorkspaceText,
  computePlayheadPercent,
  formatWorkspaceClipRange,
  formatWorkspaceTime,
  summarizeManagedTrackSync,
  type TimelineClipView,
  type TimelineRowView,
  workspaceSourceTypeLabel,
  workspaceStatusLabel,
  workspaceTrackMetaLabel
} from "./workspaceTimelineViewModel";
import {
  timelineContentBaseWidthPx,
  normalizeTimelineZoomPercent,
  timelineZoomGridSizePx,
  timelineZoomScale
} from "./workspaceTimelineGeometry";

const props = defineProps<{
  selectedClipId: string | null;
  selectedTrackId: string | null;
  playheadMs: number;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
  tracks: WorkspaceTimelineTrackDto[];
  zoomPercent?: number;
}>();

const emit = defineEmits<{
  playhead: [positionMs: number];
  "select-clip": [payload: { clipId: string; trackId: string }];
  "select-track": [trackId: string];
  trim: [payload: { clipId: string; edge: "left" | "right"; deltaMs: number }];
  "move-preview": [payload: WorkspaceTimelineMovePreview];
  "move-commit": [payload: WorkspaceTimelineMovePreview];
  "trim-preview": [payload: WorkspaceTimelineTrimPreview];
  "trim-commit": [payload: WorkspaceTimelineTrimPreview];
  "drag-cancel": [payload: WorkspaceTimelineDragPreview];
}>();

const durationMs = computed(() => {
  const clips = props.timeline?.tracks.flatMap((track) => track.clips) ?? [];
  const clipEnd = clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0);
  const declaredDuration = Math.max(0, (props.timeline?.durationSeconds ?? 0) * 1000);
  return Math.max(declaredDuration, clipEnd, 1000);
});
const safeZoomPercent = computed(() => normalizeTimelineZoomPercent(props.zoomPercent ?? 100));
const timelineContentStyle = computed(() => ({
  "--workspace-timeline-content-base-width": `${timelineContentBaseWidthPx(durationMs.value)}px`,
  "--workspace-timeline-grid-size": `${timelineZoomGridSizePx(safeZoomPercent.value)}px`,
  "--workspace-timeline-zoom-scale": String(timelineZoomScale(safeZoomPercent.value))
}));

const declaredTargetDurationMs = computed(() => Math.max(0, (props.timeline?.durationSeconds ?? 0) * 1000));

const syncTargetDurationMs = computed(() => {
  return summarizeManagedTrackSync(props.tracks, durationMs.value, declaredTargetDurationMs.value).targetDurationMs;
});

const syncTargetPercent = computed(() => computePlayheadPercent(syncTargetDurationMs.value, durationMs.value));

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

const rows = computed(() => buildTimelineRows(props.tracks, durationMs.value, syncTargetDurationMs.value));
const syncSummary = computed(() => {
  const managedRows = rows.value.filter((row) => row.isManagedAITrack);
  if (managedRows.length === 0) {
    return {
      icon: "timeline",
      label: "",
      meta: "",
      status: "synced",
      visible: false
    };
  }

  const unsyncedRows = managedRows.filter((row) => row.syncStatus !== "synced");
  const targetLabel = formatWorkspaceTime(syncTargetDurationMs.value);
  const missingRoleLabels = missingManagedTrackRoleLabels(managedRows.map((row) => row.kind));
  const managedEndMs = managedRows.map((row) =>
    row.track.clips.reduce((max, clip) => Math.max(max, clip.startMs + clip.durationMs), 0)
  );
  const presentTargetMs = managedEndMs.reduce((max, value) => Math.max(max, value), 0);
  const presentRowsAligned = managedEndMs.every((value) => Math.abs(value - presentTargetMs) <= 250);

  if (unsyncedRows.length === 0 && missingRoleLabels.length === 0) {
    return {
      icon: "check_circle",
      label: "三轨统一结束",
      meta: `${managedRows.length} 条 AI 受管轨道对齐到 ${targetLabel}`,
      status: "synced",
      visible: true
    };
  }

  if (missingRoleLabels.length > 0 && unsyncedRows.length === 0 && presentRowsAligned && presentTargetMs > 0) {
    return {
      icon: "sync_problem",
      label: `${managedRows.length} 条轨道已对齐`,
      meta: `缺少${missingRoleLabels.join("、")} · 对齐到 ${formatWorkspaceTime(presentTargetMs)}`,
      status: "warning",
      visible: true
    };
  }

  return {
    icon: "sync_problem",
    label: missingRoleLabels.length === 0 ? "三轨需要同步" : `${managedRows.length} 条轨道需要同步`,
    meta: `${unsyncedRows.length} 条 AI 受管轨道未对齐到 ${targetLabel}${missingRoleLabels.length > 0 ? ` · 缺少${missingRoleLabels.join("、")}` : ""}`,
    status: "warning",
    visible: true
  };
});

function missingManagedTrackRoleLabels(kinds: WorkspaceTimelineTrackKind[]): string[] {
  const existingKinds = new Set(kinds);
  const requiredRoles: Array<{ kind: WorkspaceTimelineTrackKind; label: string }> = [
    { kind: "video", label: "视频轨" },
    { kind: "audio", label: "配音轨" },
    { kind: "subtitle", label: "字幕轨" }
  ];

  return requiredRoles.filter((role) => !existingKinds.has(role.kind)).map((role) => role.label);
}
const draggingClipId = ref<string | null>(null);
const activeLaneElement = ref<HTMLElement | null>(null);
const timelineClips = computed(() => props.tracks.flatMap((track) => track.clips));
const snapCandidates = computed(() =>
  buildSnapCandidates(timelineClips.value, {
    movingClipId: draggingClipId.value,
    playheadMs: props.playheadMs,
    timelineEndMs: durationMs.value
  })
);
const timelineDrag = useWorkspaceTimelineDrag({
  durationMs,
  snapCandidates,
  snapThresholdMs: 120,
  minDurationMs: 500
});

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
  const preview = timelineDrag.dragPreview.value;
  const previewStartMs = preview?.clipId === clipView.id ? preview.startMs : clipView.clip.startMs;
  const previewDurationMs = preview?.clipId === clipView.id ? preview.durationMs : clipView.clip.durationMs;

  return {
    left: `${computePlayheadPercent(previewStartMs, durationMs.value)}%`,
    width: `${computePlayheadPercent(previewDurationMs, durationMs.value)}%`
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

function handleMovePointerDown(clip: WorkspaceTimelineClipDto, event: PointerEvent): void {
  if (!isPrimaryPointer(event)) return;

  const rect = resolveLaneRect(event);
  if (!rect) return;

  draggingClipId.value = clip.id;
  activeLaneElement.value = resolveLaneElement(event);
  timelineDrag.startMoveDrag({ clip, clientX: event.clientX, rect });
  bindDocumentDragEvents();
}

function handleTrimPointerDown(clip: WorkspaceTimelineClipDto, edge: WorkspaceTimelineTrimEdge, event: PointerEvent): void {
  if (!isPrimaryPointer(event)) return;

  const rect = resolveLaneRect(event);
  if (!rect) return;

  draggingClipId.value = clip.id;
  activeLaneElement.value = resolveLaneElement(event);
  timelineDrag.startTrimDrag({ clip, edge, clientX: event.clientX, rect });
  bindDocumentDragEvents();
}

function handleDocumentPointerMove(event: PointerEvent): void {
  const rect = resolveActiveLaneRect();
  if (!rect) return;

  const preview = timelineDrag.updateDrag({ clientX: event.clientX, rect });
  if (!preview) return;

  if (preview.gesture === "move") emit("move-preview", preview);
  else emit("trim-preview", preview);
}

function handleDocumentPointerUp(): void {
  const preview = timelineDrag.finishDrag();
  unbindDocumentDragEvents();
  draggingClipId.value = null;
  activeLaneElement.value = null;

  if (!preview) return;

  if (preview.gesture === "move") emit("move-commit", preview);
  else emit("trim-commit", preview);
}

function handleDocumentPointerCancel(): void {
  const preview = timelineDrag.cancelDrag();
  unbindDocumentDragEvents();
  draggingClipId.value = null;
  activeLaneElement.value = null;

  if (preview) emit("drag-cancel", preview);
}

function bindDocumentDragEvents(): void {
  document.addEventListener("pointermove", handleDocumentPointerMove, { passive: true });
  document.addEventListener("pointerup", handleDocumentPointerUp, { passive: true });
  document.addEventListener("pointercancel", handleDocumentPointerCancel, { passive: true });
}

function unbindDocumentDragEvents(): void {
  document.removeEventListener("pointermove", handleDocumentPointerMove);
  document.removeEventListener("pointerup", handleDocumentPointerUp);
  document.removeEventListener("pointercancel", handleDocumentPointerCancel);
}

function resolveLaneRect(event: PointerEvent): DOMRect | null {
  return resolveLaneElement(event)?.getBoundingClientRect() ?? null;
}

function resolveLaneElement(event: PointerEvent): HTMLElement | null {
  const target = event.currentTarget as HTMLElement | null;

  return target?.closest(".workspace-track__lane") ?? null;
}

function resolveActiveLaneRect(): DOMRect | null {
  if (!draggingClipId.value || !activeLaneElement.value) return null;

  return activeLaneElement.value.getBoundingClientRect();
}

function isPrimaryPointer(event: PointerEvent): boolean {
  return event.button === 0 && event.isPrimary;
}

function escapeCssIdentifier(value: string): string {
  return globalThis.CSS?.escape ? globalThis.CSS.escape(value) : value.replace(/["\\]/g, "\\$&");
}

onBeforeUnmount(() => {
  const preview = timelineDrag.cancelDrag();
  if (preview) emit("drag-cancel", preview);
  unbindDocumentDragEvents();
});

watch(
  () => props.selectedClipId,
  async (clipId) => {
    if (!clipId) return;
    await nextTick();
    const element = document.querySelector(`[data-clip-id="${escapeCssIdentifier(clipId)}"]`);
    if (element instanceof HTMLElement) {
      element.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }
);
</script>

<style scoped src="./WorkspaceTimeline.css"></style>
