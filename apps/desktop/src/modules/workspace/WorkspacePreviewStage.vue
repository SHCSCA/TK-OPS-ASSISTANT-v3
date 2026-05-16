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
              <div class="workspace-preview-stage__phone-top">
                <span>{{ sourceStatusLabel }}</span>
                <small>9:16</small>
              </div>
              <section class="workspace-preview-stage__content">
                <strong>{{ headline }}</strong>
                <p>{{ previewText }}</p>
              </section>
              <div class="workspace-preview-stage__caption">
                {{ previewText }}
              </div>
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
      <div class="workspace-preview-stage__transport" data-testid="workspace-preview-transport">
        <button type="button" disabled>
          <span class="material-symbols-outlined">skip_previous</span>
          <span>上一段</span>
        </button>
        <button type="button" disabled>
          <span class="material-symbols-outlined">play_arrow</span>
          <span>播放</span>
        </button>
        <time>{{ currentTimeLabel }}</time>
        <div class="workspace-preview-stage__progress" aria-label="预览进度条" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
          <span></span>
        </div>
        <time>{{ durationLabel }}</time>
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
  if (props.selectedClip) return sourceStatusLabel.value;
  const firstTrackClip = props.selectedTrack?.clips[0];
  if (firstTrackClip?.metadata?.text) return firstTrackClip.metadata.text;
  if (firstTrackClip?.metadata?.visualPrompt) return firstTrackClip.metadata.visualPrompt;
  if (props.selectedTrack) return `${props.selectedTrack.name} · ${props.selectedTrack.clips.length} 个片段`;
  return sourceStatusLabel.value;
});

const description = computed(() => {
  if (props.selectedClip) {
    return `${sourceStatusLabel.value} · ${props.selectedClip.status} · ${formatMs(props.selectedClip.durationMs)}`;
  }
  if (props.selectedTrack) {
    return `${sourceStatusLabel.value} · ${trackKindLabel(props.selectedTrack.kind)} · ${props.selectedTrack.clips.length} 个片段`;
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

const currentTimeLabel = computed(() => formatMs(activeClip.value?.startMs ?? 0));

const activeClip = computed(() => props.selectedClip ?? props.selectedTrack?.clips[0] ?? props.timeline?.tracks[0]?.clips[0] ?? null);

const sourceStatusLabel = computed(() => sourceTypeLabel(activeClip.value?.sourceType ?? null));

function sourceTypeLabel(sourceType: string | null): string {
  if (sourceType === "asset") return "资产中心素材";
  if (sourceType === "storyboard") return "分镜占位";
  if (sourceType === "imported_video") return "视频拆解";
  if (sourceType === "voice_track") return "配音片段";
  if (sourceType === "subtitle_track") return "字幕片段";
  if (!sourceType) return "暂无媒体";
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
  background:
    radial-gradient(circle at 50% 10%, color-mix(in srgb, var(--accent-primary) 22%, transparent), transparent 34%),
    linear-gradient(180deg, var(--surface-tertiary), color-mix(in srgb, var(--surface-primary) 72%, #000 28%));
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
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.12), transparent 28%),
    linear-gradient(160deg, #11161d 0%, #05070a 48%, #17120f 100%);
  border: 8px solid #080a0d;
  border-radius: 30px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.36), inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  display: grid;
  min-height: 320px;
  overflow: hidden;
  width: min(42vh, 240px);
}

.workspace-preview-stage__screen {
  display: grid;
  grid-template-rows: auto 1fr auto;
  text-align: center;
  color: #ffffff;
  min-width: 0;
  padding: 18px;
  position: relative;
}

.workspace-preview-stage__screen::before {
  background: rgba(255, 255, 255, 0.82);
  border-radius: 999px;
  content: "";
  height: 4px;
  left: 50%;
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  width: 42px;
}

.workspace-preview-stage__phone-top {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
  padding-top: 8px;
}

.workspace-preview-stage__phone-top span,
.workspace-preview-stage__phone-top small {
  background: rgba(0, 0, 0, 0.34);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  padding: 5px 8px;
}

.workspace-preview-stage__content {
  align-content: center;
  display: grid;
  gap: 12px;
  justify-items: center;
  min-width: 0;
}

.workspace-preview-stage__screen strong,
.workspace-preview-stage__screen p,
.workspace-preview-stage__caption {
  max-width: 100%;
  overflow-wrap: anywhere;
}

.workspace-preview-stage__screen strong {
  font-size: 22px;
  line-height: 1.25;
}

.workspace-preview-stage__screen p {
  color: rgba(255, 255, 255, 0.76);
  font-size: 18px;
  line-height: 1.45;
}

.workspace-preview-stage__caption {
  align-self: end;
  background: linear-gradient(180deg, transparent, rgba(0, 0, 0, 0.68));
  border-radius: 8px;
  color: #ffffff;
  font-size: 18px;
  line-height: 1.45;
  padding: 18px 10px 10px;
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
  gap: 6px;
  height: 34px;
  justify-content: center;
  padding: 0 10px;
  transition: transform var(--motion-fast) var(--ease-standard);
  cursor: pointer;
}

.workspace-preview-stage__transport time {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  min-width: 44px;
}

.workspace-preview-stage__progress {
  background: color-mix(in srgb, var(--surface-tertiary) 88%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  height: 8px;
  min-width: 120px;
  overflow: hidden;
  width: min(24vw, 220px);
}

.workspace-preview-stage__progress span {
  background: var(--accent-primary);
  display: block;
  height: 100%;
  width: 0%;
}

.workspace-preview-stage__transport button:not(:disabled):active {
  transform: scale(0.92);
}

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
