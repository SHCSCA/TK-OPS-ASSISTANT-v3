<template>
  <section class="workspace-timeline" aria-label="项目时间线">
    <div class="workspace-timeline__header">
      <strong>{{ timeline?.name ?? "时间线" }}</strong>
      <span>{{ timeline ? `${tracks.length} 条轨道` : "未创建" }}</span>
    </div>

    <div v-if="status === 'loading'" class="workspace-timeline__empty">
      正在读取时间线轨道。
    </div>
    <div v-else-if="!timeline" class="workspace-timeline__empty">
      当前项目还没有时间线草稿。
    </div>
    <div v-else-if="tracks.length === 0" class="workspace-timeline__empty">
      暂无轨道。真实素材、配音和字幕接入后会出现在这里。
    </div>
    <div v-else class="workspace-timeline__tracks">
      <div
        v-for="track in tracks"
        :key="track.id"
        class="workspace-track"
        :class="{ 'workspace-track--selected': selectedTrackId === track.id }"
      >
        <button class="workspace-track__label" type="button" @click="$emit('select-track', track.id)">
          <span class="material-symbols-outlined">{{ trackIcon(track.kind) }}</span>
          <strong>{{ track.name }}</strong>
          <small>{{ trackKindLabel(track.kind) }}</small>
        </button>
        <div class="workspace-track__lane">
          <button
            v-for="clip in track.clips"
            :key="clip.id"
            class="workspace-clip"
            :class="{ 'workspace-clip--selected': selectedClipId === clip.id }"
            type="button"
            :style="clipStyle(clip)"
            @click="$emit('select-clip', clip.id)"
          >
            {{ clip.label }}
          </button>
          <span v-if="track.clips.length === 0" class="workspace-track__empty">没有片段</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
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
  "select-clip": [clipId: string];
  "select-track": [trackId: string];
}>();

function trackIcon(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "graphic_eq";
  if (kind === "subtitle") return "subtitles";
  return "movie";
}

function trackKindLabel(kind: WorkspaceTimelineTrackKind): string {
  if (kind === "audio") return "音频";
  if (kind === "subtitle") return "字幕";
  return "视频";
}

function clipStyle(clip: WorkspaceTimelineClipDto): Record<string, string> {
  const totalMs = Math.max((props.timeline?.durationSeconds ?? 12) * 1000, 1000);
  const left = Math.min(95, (clip.startMs / totalMs) * 100);
  const width = Math.max(8, (clip.durationMs / totalMs) * 100);
  return {
    left: `${left}%`,
    width: `${Math.min(width, 100 - left)}%`
  };
}
</script>
