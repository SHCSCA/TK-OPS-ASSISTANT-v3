<template>
  <section class="panel-shell flex flex-col h-full">
    <header class="panel-heading">
      <div class="panel-heading__title">
        <span class="panel-heading__kicker">配音版本</span>
        <strong>{{ tracks.length }} 条记录</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div class="list-viewport custom-scrollbar">
      <div v-if="status === 'loading'" class="state-surface">
        <div class="loading-spinner"></div>
        <strong>正在读取配音版本</strong>
        <p>{{ stateMessage }}</p>
      </div>
      <div v-else-if="status === 'error'" class="state-surface state-surface--error">
        <span class="material-symbols-outlined text-danger">error</span>
        <strong>读取失败</strong>
        <p>{{ errorMessage || stateMessage }}</p>
      </div>
      <div v-else-if="tracks.length === 0" class="state-surface state-surface--empty">
        <span class="material-symbols-outlined text-tertiary">history</span>
        <strong>暂无历史版本</strong>
        <p>{{ stateMessage }}</p>
      </div>

      <TransitionGroup v-else name="voice-version" tag="div" class="version-list">
        <article
          v-for="track in tracks"
          :key="track.id"
          class="version-item"
          :class="{ 'version-item--active': selectedTrackId === track.id }"
          @click="$emit('select', track.id)"
        >
          <div class="version-item__head">
            <div class="version-info">
              <span class="version-voice">{{ track.voiceName }}</span>
              <span class="version-tag">{{ track.provider || "volcengine" }}</span>
            </div>
            <div class="version-badge" :data-state="track.status">
              {{ statusText(track.status) }}
            </div>
          </div>

          <div class="version-item__body">
            <div class="version-metric">
              <span class="metric-label">段落</span>
              <span class="metric-value">{{ track.segments.length }}</span>
            </div>
            <div class="version-metric">
              <span class="metric-label">修订</span>
              <span class="metric-value">v{{ track.version?.revision ?? 1 }}</span>
            </div>
          </div>

          <div class="version-item__footer">
            <span class="version-date">{{ formatDate(track.createdAt) }}</span>
            <button class="delete-link" type="button" @click.stop="confirmDelete(track.id)">
              <span class="material-symbols-outlined">delete</span>
              删除
            </button>
          </div>
        </article>
      </TransitionGroup>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { VoiceTrackDto, VoiceTrackStatus } from "@/types/runtime";
import type { VoiceStudioStatus } from "@/stores/voice-studio";

const props = defineProps<{
  errorMessage: string | null;
  selectedTrackId: string | null;
  stateMessage: string;
  status: VoiceStudioStatus;
  tracks: VoiceTrackDto[];
}>();

const emit = defineEmits<{
  delete: [trackId: string];
  select: [trackId: string];
}>();

const statusLabel = computed(() => {
  if (props.status === "loading") return "同步中";
  if (props.status === "error") return "故障";
  if (props.status === "blocked") return "阻断";
  if (props.tracks.length === 0) return "无数据";
  return "就绪";
});

function statusText(status: VoiceTrackStatus): string {
  if (status === "blocked") return "草稿";
  if (status === "ready") return "就绪";
  if (status === "generating") return "生成中";
  return "异常";
}

function formatDate(value: string): string {
  if (!value) return "未知时间";
  const date = new Date(value);
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function confirmDelete(trackId: string): void {
  if (window.confirm("确认删除这个配音版本吗？该操作不可撤销。")) {
    emit("delete", trackId);
  }
}
</script>

<style scoped>
.panel-shell {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
}

.panel-heading__title {
  display: grid;
  gap: 2px;
}

.panel-heading__kicker {
  color: var(--color-text-tertiary);
  font: var(--font-caption);
  text-transform: uppercase;
  letter-spacing: var(--ls-caption);
}

.panel-heading strong {
  color: var(--color-text-primary);
  font: var(--font-title-sm);
}

.panel-heading__chip {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font: var(--font-caption);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-default);
}

.panel-heading__chip[data-state="loading"] {
  color: var(--color-brand-primary);
  border-color: var(--color-brand-secondary);
}

.panel-heading__chip[data-state="blocked"] {
  color: var(--color-warning);
  border-color: rgba(245, 183, 64, 0.4);
}

.list-viewport {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: var(--color-border-default);
  border-radius: 3px;
}

.version-list {
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.version-item {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  text-align: left;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  display: grid;
  gap: 12px;
}

.version-item:hover {
  border-color: var(--color-brand-secondary);
  background: var(--color-bg-muted);
}

.version-item--active {
  border-color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.04);
  box-shadow: 0 0 0 1px var(--color-brand-primary);
}

.version-item__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.version-info {
  display: grid;
  gap: 2px;
}

.version-voice {
  font: var(--font-body-sm);
  font-weight: 800;
  color: var(--color-text-primary);
}

.version-tag {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-family: var(--font-code);
  text-transform: uppercase;
}

.version-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
}

.version-badge[data-state="ready"] {
  border-color: var(--color-brand-secondary);
  color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.05);
}

.version-badge[data-state="blocked"] {
  border-color: rgba(245, 183, 64, 0.4);
  color: var(--color-warning);
}

.version-item__body {
  display: flex;
  gap: var(--space-4);
}

.version-metric {
  display: grid;
  gap: 2px;
}

.metric-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.metric-value {
  font: var(--font-caption);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.version-item__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-subtle);
}

.version-date {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.delete-link {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 11px;
  cursor: pointer;
  transition: color var(--motion-fast);
  padding: 2px 4px;
  border-radius: 4px;
}

.delete-link:hover {
  color: var(--color-danger);
  background: rgba(255, 90, 99, 0.05);
}

.delete-link .material-symbols-outlined {
  font-size: 14px;
}

.state-surface {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  display: grid;
  gap: var(--space-2);
}

.state-surface strong {
  font: var(--font-title-sm);
}

.state-surface p {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.state-surface .material-symbols-outlined {
  font-size: 32px;
  margin-bottom: var(--space-2);
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border-default);
  border-top-color: var(--color-brand-primary);
  border-radius: 50%;
  margin: 0 auto var(--space-2);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.voice-version-enter-active,
.voice-version-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.voice-version-enter-from,
.voice-version-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
