<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">脚本段落</span>
        <strong>{{ paragraphs.length }} 段</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div v-if="status === 'loading'" class="state-surface">
      <strong>正在读取脚本文本和配音版本。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-else-if="status === 'error'" class="state-surface state-surface--error">
      <strong>脚本读取失败。</strong>
      <p>{{ errorMessage || stateMessage }}</p>
    </div>
    <div v-else-if="paragraphs.length === 0" class="state-surface state-surface--empty">
      <strong>脚本文本为空。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-if="status === 'blocked' && paragraphs.length > 0" class="state-surface state-surface--blocked">
      <strong>脚本已读到，但生成入口被阻断。</strong>
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
          <span class="paragraph-time">约 {{ paragraph.estimatedDuration }} 秒</span>
        </div>
        <span class="paragraph-text">{{ paragraph.text }}</span>
      </button>
    </TransitionGroup>
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
  if (props.status === "loading") return "读取中";
  if (props.status === "error") return "错误";
  if (props.status === "blocked") return "阻断";
  if (props.paragraphs.length === 0) return "空态";
  return "可用";
});
</script>

<style scoped>
.panel-shell {
  min-height: 0;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-elevated);
  overflow: hidden;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-heading > div {
  display: grid;
  gap: 4px;
}

.panel-heading__kicker {
  color: var(--text-tertiary);
  font-size: 12px;
}

.panel-heading strong {
  color: var(--brand-primary);
  font-size: 14px;
}

.panel-heading__chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.panel-heading__chip[data-state="loading"] {
  border-color: color-mix(in srgb, var(--info) 28%, transparent);
  color: var(--info);
}

.panel-heading__chip[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 28%, transparent);
  color: var(--danger);
}

.panel-heading__chip[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.paragraph-list {
  display: grid;
  gap: 10px;
  padding: 12px;
}

.paragraph-item {
  display: grid;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    background-color 160ms ease;
}

.paragraph-item:hover,
.paragraph-item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 36%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.paragraph-item:hover {
  transform: translateY(-1px);
}

.paragraph-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.paragraph-index {
  color: var(--brand-primary);
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.paragraph-time {
  color: var(--text-tertiary);
  font-size: 12px;
}

.paragraph-text {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  word-break: break-word;
}

.state-surface {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  margin: 12px;
}

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.state-surface--error {
  border-color: color-mix(in srgb, var(--danger) 24%, transparent);
}

.state-surface--empty {
  border-color: color-mix(in srgb, var(--warning) 24%, transparent);
}

.state-surface--blocked {
  border-color: color-mix(in srgb, var(--warning) 30%, transparent);
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

@media (prefers-reduced-motion: reduce) {
  .paragraph-item,
  .voice-list-enter-active,
  .voice-list-leave-active {
    transition: none;
  }

  .paragraph-item:hover {
    transform: none;
  }
}
</style>
