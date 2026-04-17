<template>
  <main class="workspace-preview-stage" aria-label="预览舞台">
    <header class="workspace-preview-stage__header">
      <div>
        <strong>预览区</strong>
        <p>{{ headerDescription }}</p>
      </div>
      <span class="workspace-preview-stage__pill">
        {{ timeline?.status ?? "未创建草稿" }}
      </span>
    </header>

    <div class="workspace-preview-stage__body">
      <div class="workspace-preview-stage__frame">
        <div class="workspace-preview-stage__canvas">
          <span class="material-symbols-outlined">movie</span>
          <strong>{{ headline }}</strong>
          <p>{{ description }}</p>
        </div>
      </div>

      <aside class="workspace-preview-stage__facts">
        <div>
          <small>时间线</small>
          <strong>{{ timeline?.name ?? "未创建" }}</strong>
        </div>
        <div>
          <small>当前选择</small>
          <strong>{{ selectionLabel }}</strong>
        </div>
        <div>
          <small>总时长</small>
          <strong>{{ durationLabel }}</strong>
        </div>
        <div>
          <small>轨道数</small>
          <strong>{{ trackCountLabel }}</strong>
        </div>
      </aside>
    </div>

    <footer class="workspace-preview-stage__footer">
      <div class="workspace-preview-stage__transport">
        <button type="button" disabled>
          <span class="material-symbols-outlined">fast_rewind</span>
        </button>
        <button type="button" disabled>
          <span class="material-symbols-outlined">play_arrow</span>
        </button>
        <button type="button" disabled>
          <span class="material-symbols-outlined">fast_forward</span>
        </button>
      </div>
      <p>
        真实媒体预览尚未接入，本阶段不展示伪进度或伪画面。
        <span v-if="blockedMessage">{{ blockedMessage }}</span>
      </p>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type {
  WorkspaceTimelineClipDto,
  WorkspaceTimelineDto,
  WorkspaceTimelineTrackDto
} from "@/types/runtime";

const props = defineProps<{
  blockedMessage: string | null;
  selectedClip: WorkspaceTimelineClipDto | null;
  selectedTrack: WorkspaceTimelineTrackDto | null;
  timeline: WorkspaceTimelineDto | null;
}>();

const selectionLabel = computed(() => {
  if (props.selectedClip) return props.selectedClip.label;
  if (props.selectedTrack) return props.selectedTrack.name;
  return "尚未选中片段";
});

const headerDescription = computed(() => {
  if (!props.timeline) return "等待创建时间线草稿。";
  if (props.selectedClip) return "当前选中片段已与时间线和检查器联动。";
  if (props.selectedTrack) return "当前选中轨道已与时间线和检查器联动。";
  return "预览区保留工作台骨架，等待真实媒体预览接入。";
});

const headline = computed(() => {
  if (props.selectedClip) return props.selectedClip.label;
  if (props.selectedTrack) return props.selectedTrack.name;
  if (props.timeline) return "主预览未接入";
  return "等待时间线草稿";
});

const description = computed(() => {
  if (props.selectedClip) {
    return `${sourceTypeLabel(props.selectedClip.sourceType)} · ${props.selectedClip.status} · ${formatMs(props.selectedClip.durationMs)}`;
  }
  if (props.selectedTrack) {
    return `${trackKindLabel(props.selectedTrack.kind)} · ${props.selectedTrack.clips.length} 个片段`;
  }
  if (props.timeline) {
    return "当前只保留真实时间线选择态，不伪造播放进度。";
  }
  return "先创建空草稿，再把真实片段、音轨和字幕落到同一条时间线。";
});

const durationLabel = computed(() => {
  const seconds = props.timeline?.durationSeconds;
  if (seconds === null || seconds === undefined) return "待定";
  return formatMs(seconds * 1000);
});

const trackCountLabel = computed(() => `${props.timeline?.tracks.length ?? 0} 条`);

function sourceTypeLabel(sourceType: string): string {
  if (sourceType === "asset") return "资产中心";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音中心";
  if (sourceType === "subtitle_track") return "字幕对齐";
  return "手动片段";
}

function trackKindLabel(kind: WorkspaceTimelineTrackDto["kind"]): string {
  if (kind === "audio") return "音频轨";
  if (kind === "subtitle") return "字幕轨";
  return "视频轨";
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
.workspace-preview-stage {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 24px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 16px;
  padding: 18px;
}

.workspace-preview-stage__header,
.workspace-preview-stage__body,
.workspace-preview-stage__footer,
.workspace-preview-stage__transport {
  align-items: center;
  display: flex;
  gap: 14px;
  justify-content: space-between;
}

.workspace-preview-stage__header p,
.workspace-preview-stage__canvas p,
.workspace-preview-stage__footer p {
  color: var(--text-secondary);
  margin: 0;
}

.workspace-preview-stage__pill,
.workspace-preview-stage__facts small {
  color: var(--text-tertiary);
}

.workspace-preview-stage__pill {
  background: color-mix(in srgb, var(--surface-tertiary) 94%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  font-size: 12px;
  padding: 6px 12px;
}

.workspace-preview-stage__body {
  align-items: stretch;
}

.workspace-preview-stage__frame {
  background:
    radial-gradient(circle at top, color-mix(in srgb, var(--brand-primary) 16%, transparent), transparent 56%),
    var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 22px;
  display: grid;
  flex: 1;
  min-height: 320px;
  padding: 18px;
}

.workspace-preview-stage__canvas {
  align-content: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  text-align: center;
}

.workspace-preview-stage__canvas .material-symbols-outlined {
  font-size: 44px;
}

.workspace-preview-stage__facts {
  align-content: start;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 18px;
  display: grid;
  gap: 12px;
  min-width: 220px;
  padding: 16px;
}

.workspace-preview-stage__facts div {
  display: grid;
  gap: 4px;
}

.workspace-preview-stage__transport button {
  align-items: center;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  display: inline-flex;
  height: 34px;
  justify-content: center;
  width: 34px;
}

@media (max-width: 960px) {
  .workspace-preview-stage__body,
  .workspace-preview-stage__footer {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-preview-stage__facts {
    min-width: 0;
  }
}
</style>
