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
        <div v-if="selectedTrack?.filePath" class="player-wrapper">
          <audio
            class="audio-player"
            controls
            :src="selectedTrack.filePath"
          />
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
import { computed } from "vue";

import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";
import type { VoiceProfileDto, VoiceTrackDto } from "@/types/runtime";

const props = defineProps<{
  activeParagraph: Paragraph | null;
  generationMessage: string | null;
  selectedProfile: VoiceProfileDto | null;
  selectedTrack: VoiceTrackDto | null;
  stateMessage: string;
  status: VoiceStudioStatus;
}>();

const bars = Array.from({ length: 48 }, (_, index) => ({
  height: 15 + Math.random() * 70,
  index
}));

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
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  height: 100%;
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
  font: var(--font-display-sm);
  color: var(--color-text-primary);
  letter-spacing: var(--ls-display-sm);
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
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-height: 0;
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
  flex: 1;
  min-height: 140px;
  background: #0a0c10;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-6);
  position: relative;
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.5);
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
  background: linear-gradient(to top, var(--color-brand-primary), #4dd0e1);
  border-radius: var(--radius-full);
  opacity: 0.6;
  transition: height 0.3s ease;
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

.audio-player {
  width: 100%;
  height: 40px;
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

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
