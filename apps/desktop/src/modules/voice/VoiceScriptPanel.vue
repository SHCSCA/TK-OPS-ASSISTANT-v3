<template>
  <section class="panel-shell flex flex-col h-full">
    <header class="panel-heading">
      <div class="panel-heading__title">
        <span class="panel-heading__kicker">脚本段落</span>
        <strong>{{ paragraphs.length }} 段</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div class="list-viewport custom-scrollbar">
      <div v-if="status === 'loading'" class="state-surface">
        <div class="loading-spinner"></div>
        <strong>正在读取脚本文本</strong>
        <p>{{ stateMessage }}</p>
      </div>
      <div v-else-if="status === 'error'" class="state-surface state-surface--error">
        <span class="material-symbols-outlined text-danger">error</span>
        <strong>读取失败</strong>
        <p>{{ errorMessage || stateMessage }}</p>
      </div>
      <div v-else-if="paragraphs.length === 0" class="state-surface state-surface--empty">
        <span class="material-symbols-outlined text-tertiary">article</span>
        <strong>脚本文本为空</strong>
        <p>{{ stateMessage }}</p>
      </div>
      <div v-if="status === 'blocked' && paragraphs.length > 0" class="state-surface state-surface--blocked">
        <span class="material-symbols-outlined text-warning">block</span>
        <strong>生成入口被阻断</strong>
        <p>{{ stateMessage }}</p>
      </div>

      <TransitionGroup v-if="paragraphs.length > 0" name="voice-list" tag="div" class="paragraph-list">
        <button
          v-for="(paragraph, index) in paragraphs"
          :key="`${index}-${paragraph.text}`"
          class="paragraph-item"
          :class="{ 'paragraph-item--active': activeIndex === index }"
          type="button"
          @click="$emit('select', index)"
        >
          <div class="paragraph-item__top">
            <span class="paragraph-index">{{ String(index + 1).padStart(2, "0") }}</span>
            <span class="paragraph-time">
              <span class="material-symbols-outlined">schedule</span>
              约 {{ paragraph.estimatedDuration }} 秒
            </span>
          </div>
          <p class="paragraph-text">{{ paragraph.text }}</p>
        </button>
      </TransitionGroup>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";

const props = defineProps<{
  activeIndex: number;
  errorMessage: string | null;
  paragraphs: Paragraph[];
  stateMessage: string;
  status: VoiceStudioStatus;
}>();

defineEmits<{
  select: [index: number];
}>();

const statusLabel = computed(() => {
  if (props.status === "loading") return "同步中";
  if (props.status === "error") return "故障";
  if (props.status === "blocked") return "阻断";
  if (props.paragraphs.length === 0) return "无数据";
  return "就绪";
});
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
  color: var(--color-brand-primary);
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

.paragraph-list {
  padding: var(--space-3);
  display: grid;
  gap: var(--space-2);
}

.paragraph-item {
  width: 100%;
  padding: var(--space-4);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: grid;
  gap: 8px;
}

.paragraph-item:hover {
  border-color: var(--color-brand-secondary);
  background: var(--color-bg-muted);
}

.paragraph-item--active {
  border-color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.04);
  box-shadow: 0 0 0 1px var(--color-brand-primary);
}

.paragraph-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.paragraph-index {
  font: var(--font-caption);
  font-weight: 800;
  color: var(--color-brand-primary);
  background: rgba(0, 188, 212, 0.1);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.paragraph-time {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.paragraph-time .material-symbols-outlined {
  font-size: 14px;
}

.paragraph-text {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
  line-height: 1.6;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  word-break: break-word;
}

.paragraph-item--active .paragraph-text {
  color: var(--color-text-primary);
}

.state-surface {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  display: grid;
  gap: var(--space-2);
}

.state-surface strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
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

.voice-list-enter-active,
.voice-list-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.voice-list-enter-from,
.voice-list-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
