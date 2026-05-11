<template>
  <section class="panel-shell" data-testid="voice-preview-stage">
    <div class="stage-overlay"></div>

    <div class="stage-content">
      <header class="stage-header">
        <div class="stage-header__info">
          <span class="stage-kicker">
            <span class="material-symbols-outlined">theater_comedy</span>
            配音导演台
          </span>
          <h2 class="stage-title">{{ title }}</h2>
        </div>
        <div class="stage-badges">
          <span class="badge" :data-state="status">{{ statusLabel }}</span>
          <span v-if="selectedTrack" class="badge badge--revision">v{{ selectedTrack.version?.revision ?? 1 }}</span>
        </div>
      </header>

      <div class="stage-body">
        <div class="context-card">
          <div class="context-card__icon">
            <span class="material-symbols-outlined">format_quote</span>
          </div>
          <p class="context-text">{{ stageCopy }}</p>
        </div>

        <div class="wave-container" :class="{ 'wave-container--busy': status === 'generating' }">
          <div class="wave-viz">
            <div
              v-for="bar in bars"
              :key="bar.index"
              class="wave-bar"
              :style="{
                height: `${bar.height}%`,
                animationDelay: `${bar.index * 0.05}s`
              }"
            />
          </div>
          <div class="wave-placeholder" v-if="!selectedTrack && status !== 'generating'">
            <span class="material-symbols-outlined">graphic_eq</span>
            <p>等待生成音频波形</p>
          </div>
        </div>

        <div class="meta-dashboard">
          <div class="meta-item">
            <span class="meta-label">音色角色</span>
            <span class="meta-value">{{ selectedProfile?.displayName ?? "未选择" }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">语种</span>
            <span class="meta-value">{{ selectedProfile ? formatLocale(selectedProfile.locale) : "--" }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">片段数量</span>
            <span class="meta-value">{{ selectedTrack?.segments.length ?? 0 }} 段</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Provider</span>
            <span class="meta-value">{{ selectedTrack?.provider || "火山豆包" }}</span>
          </div>
        </div>
      </div>

      <footer class="stage-footer">
        <div v-if="audioSrc" class="player-wrapper">
          <div class="preview-mode-row">
            <div class="preview-mode-group" role="group" aria-label="预览范围">
              <button
                class="preview-mode-button"
                :class="{ 'preview-mode-button--active': previewMode === 'full' }"
                data-testid="voice-preview-mode-full"
                type="button"
                @click="selectPreviewMode('full')"
              >
                整段
              </button>
              <button
                class="preview-mode-button"
                :class="{ 'preview-mode-button--active': previewMode === 'segment' }"
                data-testid="voice-preview-mode-segment"
                :disabled="segmentPreviewDisabled"
                type="button"
                @click="selectPreviewMode('segment')"
              >
                当前段落
              </button>
            </div>
            <span class="preview-range-label">{{ previewRangeLabel }}</span>
          </div>
          <audio
            ref="audioRef"
            class="audio-player"
            controls
            preload="metadata"
            :src="audioSrc"
            @error="handleAudioError"
            @loadedmetadata="handleLoadedMetadata"
            @play="handleAudioPlay"
            @timeupdate="handleAudioTimeUpdate"
          />
          <p v-if="audioLoadError" class="audio-error">{{ audioLoadError }}</p>
        </div>
        <div v-else class="status-tip">
          <span class="material-symbols-outlined">{{ statusIcon }}</span>
          <span>{{ statusMessage }}</span>
        </div>
      </footer>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { buildVoiceTrackAudioUrl } from "@/app/runtime-client";
import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";
import type { VoiceProfileDto, VoiceTrackDto } from "@/types/runtime";
import {
  buildVoicePreviewRanges,
  formatPreviewTime,
  type VoicePreviewRange
} from "./voice-preview-ranges";

type PreviewMode = "full" | "segment";

const props = withDefaults(defineProps<{
  activeParagraph: Paragraph | null;
  activeParagraphIndex?: number;
  generationMessage: string | null;
  paragraphs?: Paragraph[];
  selectedProfile: VoiceProfileDto | null;
  selectedTrack: VoiceTrackDto | null;
  stateMessage: string;
  status: VoiceStudioStatus;
}>(), {
  activeParagraphIndex: 0,
  paragraphs: () => []
});

const bars = Array.from({ length: 48 }, (_, index) => ({
  height: 15 + Math.random() * 70,
  index
}));
const audioLoadError = ref<string | null>(null);
const audioDurationSec = ref<number | null>(null);
const audioRef = ref<HTMLAudioElement | null>(null);
const previewMode = ref<PreviewMode>("full");

const audioSrc = computed(() => {
  if (!props.selectedTrack?.filePath) {
    return "";
  }
  return buildVoiceTrackAudioUrl(
    props.selectedTrack.id,
    props.selectedTrack.updatedAt ?? props.selectedTrack.createdAt
  );
});

watch(audioSrc, () => {
  audioLoadError.value = null;
  audioDurationSec.value = null;
});

const safeParagraphs = computed(() => (Array.isArray(props.paragraphs) ? props.paragraphs : []));
const safeActiveParagraphIndex = computed(() => {
  const rawIndex = Number(props.activeParagraphIndex);
  if (!Number.isFinite(rawIndex) || rawIndex < 0) {
    return 0;
  }

  const maxIndex = Math.max(0, safeParagraphs.value.length - 1);
  return Math.min(Math.floor(rawIndex), maxIndex);
});

watch(
  safeActiveParagraphIndex,
  () => {
    if (previewMode.value === "segment") {
      seekToSegmentStart();
    }
  }
);

const previewRanges = computed(() =>
  buildVoicePreviewRanges(safeParagraphs.value, audioDurationSec.value)
);
const activeSegmentRange = computed<VoicePreviewRange | null>(() =>
  previewRanges.value.find((range) => range.index === safeActiveParagraphIndex.value) ?? null
);
const segmentPreviewDisabled = computed(() => !audioSrc.value || activeSegmentRange.value === null);
const previewRangeLabel = computed(() => {
  if (previewMode.value === "segment" && activeSegmentRange.value) {
    return [
      `当前段落预览：第 ${safeActiveParagraphIndex.value + 1} 段`,
      `${formatPreviewTime(activeSegmentRange.value.startSec)} - ${formatPreviewTime(activeSegmentRange.value.endSec)}`
    ].join(" ");
  }

  const endSec = audioDurationSec.value ?? previewRanges.value.at(-1)?.endSec ?? 0;
  return `整段预览：${formatPreviewTime(0)} - ${formatPreviewTime(endSec)}`;
});

const title = computed(() => {
  if (props.status === "generating") return "正在生成配音版本...";
  if (props.status === "blocked") return "配音能力暂时受阻";
  if (props.status === "error") return "发现配置异常";
  if (!props.selectedTrack) return "等待创作指令";
  return "导演台已就绪";
});

const stageCopy = computed(() => {
  if (!props.activeParagraph) return "请在左侧选择一段脚本文稿，开始您的配音创作。";
  return props.activeParagraph.text;
});

const statusLabel = computed(() => {
  if (props.status === "loading") return "同步中";
  if (props.status === "generating") return "正在生成";
  if (props.status === "blocked") return "已阻断";
  if (props.status === "error") return "故障";
  if (!props.selectedTrack) return "空态";
  return "就绪";
});

const statusIcon = computed(() => {
  if (props.status === "generating") return "sync";
  if (props.status === "blocked") return "block";
  if (props.status === "error") return "error";
  return "info";
});

const statusMessage = computed(() => {
  if (props.status === "loading") return "正在同步环境配置...";
  if (props.status === "generating") return "正在将文稿转化为音频流，请稍后。";
  if (props.status === "blocked") {
    return props.generationMessage || "由于缺少 Provider 配置，生成任务已阻断。";
  }
  if (props.status === "error") return props.stateMessage || "配音系统发生未知错误。";
  if (!props.selectedTrack) {
    return "请点击右上角“生成整片音轨”开始配音任务。";
  }
  return props.stateMessage;
});

function formatLocale(locale: string) {
  if (locale.startsWith("zh")) return "中文 (Mandarin)";
  if (locale.startsWith("en")) return "英语 (English)";
  return locale;
}

function formatDate(value: string): string {
  if (!value) return "--";
  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function handleAudioError(): void {
  audioLoadError.value = "音频文件加载失败，请重新生成或检查 Runtime。";
}

function selectPreviewMode(mode: PreviewMode): void {
  if (mode === "segment" && segmentPreviewDisabled.value) {
    return;
  }
  previewMode.value = mode;
  if (mode === "segment") {
    seekToSegmentStart();
  }
}

function handleLoadedMetadata(event: Event): void {
  const audio = event.currentTarget as HTMLAudioElement;
  audioDurationSec.value = Number.isFinite(audio.duration) && audio.duration > 0
    ? audio.duration
    : null;
  audioLoadError.value = null;
  if (previewMode.value === "segment") {
    seekToSegmentStart();
  }
}

function handleAudioPlay(event: Event): void {
  if (previewMode.value !== "segment" || !activeSegmentRange.value) {
    return;
  }

  const audio = event.currentTarget as HTMLAudioElement;
  if (
    audio.currentTime < activeSegmentRange.value.startSec ||
    audio.currentTime >= activeSegmentRange.value.endSec
  ) {
    audio.currentTime = activeSegmentRange.value.startSec;
  }
}

function handleAudioTimeUpdate(event: Event): void {
  if (previewMode.value !== "segment" || !activeSegmentRange.value) {
    return;
  }

  const audio = event.currentTarget as HTMLAudioElement;
  if (audio.currentTime < activeSegmentRange.value.startSec - 0.1) {
    audio.currentTime = activeSegmentRange.value.startSec;
    return;
  }
  if (audio.currentTime >= activeSegmentRange.value.endSec) {
    audio.pause();
    audio.currentTime = activeSegmentRange.value.endSec;
  }
}

function seekToSegmentStart(): void {
  if (!audioRef.value || !activeSegmentRange.value) {
    return;
  }
  audioRef.value.currentTime = activeSegmentRange.value.startSec;
}
</script>

<style scoped>
.panel-shell {
  position: relative;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  align-self: start;
}

.stage-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 200px;
  background: linear-gradient(to bottom, rgba(0, 188, 212, 0.08), transparent);
  pointer-events: none;
}

.stage-content {
  position: relative;
  z-index: 1;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stage-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.stage-kicker {
  display: flex;
  align-items: center;
  gap: 6px;
  font: var(--font-caption);
  font-weight: 800;
  color: var(--color-brand-primary);
  text-transform: uppercase;
  letter-spacing: var(--ls-caption);
  margin-bottom: 4px;
}

.stage-kicker .material-symbols-outlined {
  font-size: 16px;
}

.stage-title {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
  letter-spacing: var(--ls-title-lg);
}

.stage-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font: var(--font-caption);
  font-weight: 600;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-default);
  color: var(--color-text-secondary);
}

.badge[data-state="generating"] {
  background: rgba(0, 188, 212, 0.1);
  color: var(--color-brand-primary);
  border-color: var(--color-brand-secondary);
}

.badge[data-state="blocked"] {
  background: rgba(245, 183, 64, 0.1);
  color: var(--color-warning);
  border-color: rgba(245, 183, 64, 0.3);
}

.badge--revision {
  font-family: var(--font-code);
  color: var(--color-text-tertiary);
}

.stage-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.context-card {
  position: relative;
  padding: var(--space-5) var(--space-6);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-brand-primary);
}

.context-card__icon {
  position: absolute;
  top: 10px;
  right: 12px;
  opacity: 0.1;
}

.context-card__icon .material-symbols-outlined {
  font-size: 48px;
}

.context-text {
  margin: 0;
  font: var(--font-title-sm);
  line-height: 1.6;
  color: var(--color-text-primary);
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.wave-container {
  height: 120px;
  flex-shrink: 0;
  background: var(--color-bg-inset, var(--color-bg-muted));
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-6);
  position: relative;
}

.wave-viz {
  width: 100%;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.wave-bar {
  flex: 1;
  max-width: 6px;
  background: linear-gradient(to top, var(--color-brand-primary), var(--color-brand-secondary, #5E17EB));
  border-radius: var(--radius-full);
  opacity: 0.6;
  transition: height var(--motion-default) ease;
}

.wave-container--busy .wave-bar {
  animation: wave-pulse 1s ease-in-out infinite;
}

.wave-placeholder {
  position: absolute;
  text-align: center;
  color: var(--color-text-tertiary);
}

.wave-placeholder .material-symbols-outlined {
  font-size: 40px;
  margin-bottom: 8px;
  opacity: 0.3;
}

.wave-placeholder p {
  margin: 0;
  font: var(--font-caption);
}

.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.meta-item {
  display: grid;
  gap: 4px;
}

.meta-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font: var(--font-caption);
  font-weight: 700;
  color: var(--color-text-secondary);
}

.stage-footer {
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.player-wrapper {
  background: var(--color-bg-muted);
  padding: 8px;
  border-radius: var(--radius-md);
}

.preview-mode-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: 8px;
}

.preview-mode-group {
  display: inline-flex;
  padding: 2px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
}

.preview-mode-button {
  border: 0;
  border-radius: calc(var(--radius-md) - 2px);
  padding: 4px 10px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font: var(--font-caption);
}

.preview-mode-button--active {
  background: rgba(0, 188, 212, 0.1);
  color: var(--color-brand-primary);
  font-weight: 700;
}

.preview-mode-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.preview-range-label {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
  text-align: right;
}

.audio-player {
  width: 100%;
  height: 40px;
}

.audio-error {
  margin: 6px 0 0;
  color: var(--color-danger);
  font: var(--font-caption);
}

.status-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  justify-content: center;
}

.status-tip .material-symbols-outlined {
  font-size: 20px;
}

@keyframes wave-pulse {
  0%, 100% { height: 20%; opacity: 0.4; }
  50% { height: 90%; opacity: 0.9; }
}

/* @keyframes spin 由全局 base.css 统一定义 */
</style>
