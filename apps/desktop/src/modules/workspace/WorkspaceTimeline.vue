<template>
  <section class="workspace-timeline" aria-label="项目时间线" :data-state="status">
    <header class="workspace-timeline__header">
      <div>
        <strong>{{ timeline?.name ?? "时间线" }}</strong>
        <p>{{ subtitle }}</p>
      </div>
      <span class="workspace-timeline__pill">
        {{ selectedSummary }}
      </span>
    </header>

    <div v-if="status === 'loading'" class="workspace-timeline__empty">
      正在读取时间线轨道。
    </div>
    <div v-else-if="!timeline" class="workspace-timeline__empty">
      当前项目还没有时间线草稿。
    </div>
    <div v-else-if="tracks.length === 0" class="workspace-timeline__empty">
      当前时间线还没有轨道，不补示例轨道。
    </div>
    <div v-else class="workspace-timeline__body">
      <div v-if="status === 'saving'" class="ai-flow-bar" />
      <div class="workspace-timeline__ruler">
        <span
          v-for="marker in markers"
          :key="marker.label"
          class="workspace-timeline__tick"
          :style="{ left: marker.left }"
        >
          {{ marker.label }}
        </span>
      </div>

      <div class="workspace-timeline__tracks scroll-area">
        <transition-group name="track-list">
          <article
            v-for="track in tracks"
            :key="track.id"
            class="workspace-track"
            :class="{ 'workspace-track--selected': selectedTrackId === track.id }"
          >
            <button class="workspace-track__label" type="button" @click="$emit('select-track', track.id)">
              <span class="material-symbols-outlined">{{ trackIcon(track.kind) }}</span>
              <div>
                <strong>{{ track.name }}</strong>
                <small>{{ trackKindLabel(track.kind) }} · {{ track.clips.length }} 个片段</small>
              </div>
            </button>

            <div class="workspace-track__lane">
              <transition-group name="clip-list">
                <button
                  v-for="clip in track.clips"
                  :key="clip.id"
                  class="workspace-clip"
                  :class="{
                    'workspace-clip--selected': selectedClipId === clip.id
                  }"
                  :data-status="clip.status"
                  type="button"
                  :style="clipStyle(clip)"
                  @click="$emit('select-clip', { clipId: clip.id, trackId: track.id })"
                >
                  <strong>{{ clip.label }}</strong>
                  <small>{{ sourceTypeLabel(clip.sourceType) }} · {{ formatMs(clip.durationMs) }}</small>
                </button>
              </transition-group>
              <span v-if="track.clips.length === 0" class="workspace-track__empty">当前轨道暂无片段</span>
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

const props = defineProps<{
  selectedClipId: string | null;
  selectedTrackId: string | null;
  status: EditingWorkspaceStatus;
  timeline: WorkspaceTimelineDto | null;
  tracks: WorkspaceTimelineTrackDto[];
}>();

defineEmits<{
  "select-clip": [payload: { clipId: string; trackId: string }];
  "select-track": [trackId: string];
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
      label: formatMs(durationMs.value * ratio),
      left: `${ratio * 100}%`
    };
  });
});

const subtitle = computed(() => {
  if (!props.timeline) return "等待创建时间线草稿";
  return `${props.tracks.length} 条轨道 · ${formatMs(durationMs.value)}`;
});

const selectedSummary = computed(() => {
  if (props.selectedClipId) return "已联动到片段";
  if (props.selectedTrackId) return "已联动到轨道";
  return "点击片段查看详情";
});

function trackIcon(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "graphic_eq";
  if (kind === "subtitle") return "subtitles";
  return "movie";
}

function trackKindLabel(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "音频轨";
  if (kind === "subtitle") return "字幕轨";
  return "视频轨";
}

function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "asset") return "资产";
  if (sourceType === "imported_video") return "拆解";
  if (sourceType === "voice_track") return "配音";
  if (sourceType === "subtitle_track") return "字幕";
  return "手动";
}

function clipStyle(clip: WorkspaceTimelineClipDto): Record<string, string> {
  const totalMs = durationMs.value;
  const left = Math.min(96, (clip.startMs / totalMs) * 100);
  const width = Math.max(10, (clip.durationMs / totalMs) * 100);
  return {
    left: `${left}%`,
    width: `${Math.min(width, 100 - left)}%`
  };
}

function formatMs(value: number): string {
  const totalSeconds = Math.max(0, Math.floor(value / 1000));
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
</script>

<style scoped>
.workspace-timeline {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 22px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 16px;
  padding: 18px;
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

.workspace-timeline__header p,
.workspace-track__label small,
.workspace-track__empty,
.workspace-timeline__empty {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-timeline__pill {
  background: color-mix(in srgb, var(--surface-tertiary) 94%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 12px;
}

.workspace-timeline__empty {
  background: var(--surface-tertiary);
  border: 1px dashed var(--border-default);
  border-radius: 18px;
  padding: 18px;
}

.workspace-timeline__body {
  display: grid;
  gap: 16px;
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
  border-bottom: 1px solid var(--border-default);
  min-height: 34px;
  position: relative;
}

.workspace-timeline__tick {
  color: var(--text-tertiary);
  font-size: 11px;
  position: absolute;
  top: 0;
  transform: translateX(-50%);
}

.workspace-timeline__tracks {
  display: grid;
  gap: 12px;
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
  background: var(--surface-tertiary);
  border: 1px solid transparent;
  border-radius: 18px;
  padding: 14px;
}

.workspace-track--selected {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.workspace-track__label {
  align-items: center;
  background: transparent;
  border: 0;
  color: inherit;
  min-width: 180px;
  padding: 0;
  text-align: left;
}

.workspace-track__lane {
  background: color-mix(in srgb, var(--surface-secondary) 84%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  min-height: 84px;
  position: relative;
}

.workspace-clip {
  align-content: start;
  background: color-mix(in srgb, var(--brand-primary) 14%, var(--surface-secondary));
  border: 1px solid transparent;
  border-radius: 12px;
  color: var(--text-primary);
  display: grid;
  gap: 4px;
  min-height: 52px;
  padding: 10px 12px;
  position: absolute;
  top: 14px;
  transition: all var(--motion-fast) var(--ease-standard);
  cursor: pointer;
}

.workspace-clip:active {
  transform: scale(0.98);
}

.workspace-clip--selected {
  border-color: color-mix(in srgb, var(--brand-primary) 38%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 32%, transparent);
}

/* List Transitions */
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
  background: color-mix(in srgb, var(--color-warning) 18%, var(--surface-secondary));
}

.workspace-clip[data-status="error"],
.workspace-clip[data-status="missing_source"] {
  background: color-mix(in srgb, var(--color-danger) 18%, var(--surface-secondary));
}

.workspace-clip small {
  color: var(--text-secondary);
}

.workspace-track__empty {
  left: 16px;
  position: absolute;
  top: 28px;
}

@media (max-width: 960px) {
  .workspace-timeline__header,
  .workspace-track {
    flex-direction: column;
  }

  .workspace-track__label {
    min-width: 0;
  }
}
</style>
