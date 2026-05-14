<template>
  <main class="workspace-preview-stage" aria-label="预览舞台">
    <header class="workspace-preview-stage__header">
      <div>
        <strong>播放器</strong>
        <p>{{ headerDescription }}</p>
      </div>
      <span class="workspace-preview-stage__pill">
        {{ timeline?.status ?? "未创建草稿" }}
      </span>
    </header>

    <div class="workspace-preview-stage__body">
      <div class="workspace-preview-stage__viewer">
        <div class="workspace-preview-stage__phone" data-testid="workspace-preview-phone" data-ratio="9:16">
          <transition name="preview-fade" mode="out-in">
            <div :key="headline" class="workspace-preview-stage__screen">
              <small>9:16</small>
              <strong>{{ headline }}</strong>
              <p>{{ previewText }}</p>
            </div>
          </transition>
        </div>
      </div>

      <aside class="workspace-preview-stage__facts scroll-area">
        <div class="fact-item">
          <small>时间线</small>
          <strong>{{ timeline?.name ?? "未创建" }}</strong>
        </div>
        <div class="fact-item">
          <small>当前选择</small>
          <strong>{{ selectionLabel }}</strong>
        </div>
        <div class="fact-item">
          <small>总时长</small>
          <strong>{{ durationLabel }}</strong>
        </div>
        <div class="fact-item">
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
      <p>{{ description }}</p>
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
  if (props.selectedClip) return `${sourceTypeLabel(props.selectedClip.sourceType)} · ${formatMs(props.selectedClip.durationMs)}`;
  if (props.selectedTrack) return `${trackKindLabel(props.selectedTrack.kind)} · ${props.selectedTrack.clips.length} 个片段`;
  return "选择时间线片段后查看画面上下文。";
});

const headline = computed(() => {
  if (props.selectedClip) return props.selectedClip.label;
  if (props.selectedTrack) return props.selectedTrack.name;
  if (props.timeline) return "主播放器";
  return "等待时间线草稿";
});

const previewText = computed(() => {
  if (props.selectedClip?.metadata?.text) return props.selectedClip.metadata.text;
  if (props.selectedClip?.metadata?.visualPrompt) return props.selectedClip.metadata.visualPrompt;
  if (props.selectedClip) return sourceTypeLabel(props.selectedClip.sourceType);
  if (props.selectedTrack) return `${props.selectedTrack.name} · ${props.selectedTrack.clips.length} 个片段`;
  return "暂无画面";
});

const description = computed(() => {
  if (props.selectedClip) {
    return `${sourceTypeLabel(props.selectedClip.sourceType)} · ${props.selectedClip.status} · ${formatMs(props.selectedClip.durationMs)}`;
  }
  if (props.selectedTrack) {
    return `${trackKindLabel(props.selectedTrack.kind)} · ${props.selectedTrack.clips.length} 个片段`;
  }
  if (props.timeline) {
    return props.blockedMessage ?? "时间线已载入。";
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
  if (sourceType === "storyboard") return "分镜规划";
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
  border-radius: 8px;
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
.workspace-preview-stage__screen p,
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

.workspace-preview-stage__viewer {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: flex;
  flex: 1;
  justify-content: center;
  min-height: 360px;
  padding: 18px;
}

.workspace-preview-stage__phone {
  aspect-ratio: 9 / 16;
  background: #07090b;
  border: 1px solid color-mix(in srgb, var(--color-text-primary) 12%, transparent);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  display: grid;
  min-height: 320px;
  overflow: hidden;
  width: min(42vh, 240px);
}

.workspace-preview-stage__screen {
  align-content: center;
  display: grid;
  gap: 10px;
  justify-items: center;
  text-align: center;
  color: #ffffff;
  padding: 24px;
}

.workspace-preview-stage__screen small {
  color: rgba(255, 255, 255, 0.58);
}

.workspace-preview-stage__screen p {
  color: rgba(255, 255, 255, 0.76);
}

.workspace-preview-stage__screen strong,
.workspace-preview-stage__screen p {
  max-width: 100%;
  overflow-wrap: anywhere;
}

.workspace-preview-stage__screen strong {
  font-size: 20px;
  line-height: 1.25;
}

.workspace-preview-stage__facts {
  align-content: start;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  display: grid;
  gap: 12px;
  min-width: 220px;
  padding: 16px;
}

.workspace-preview-stage__facts div {
  display: grid;
  gap: 4px;
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
  transition: transform var(--motion-fast) var(--ease-standard);
  cursor: pointer;
}

.workspace-preview-stage__transport button:not(:disabled):active {
  transform: scale(0.92);
}

/* Transitions */
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard), transform var(--motion-default) var(--ease-spring);
}
.preview-fade-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.preview-fade-leave-to {
  opacity: 0;
  transform: scale(1.02);
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
