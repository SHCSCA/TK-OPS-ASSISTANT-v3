<template>
  <section class="voice-script-panel">
    <header class="panel-heading">
      <span>脚本段落</span>
      <strong>{{ paragraphs.length }}</strong>
    </header>

    <div v-if="status === 'loading'" class="state state--muted">
      正在读取脚本文本和配音版本。
    </div>
    <div v-else-if="errorMessage" class="state state--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="paragraphs.length === 0" class="state state--muted">
      请先在脚本与选题中心创建内容。
    </div>

    <TransitionGroup v-else name="voice-list" tag="div" class="paragraph-list">
      <button
        v-for="(paragraph, index) in paragraphs"
        :key="`${index}-${paragraph.text}`"
        class="paragraph-item"
        :class="{ 'paragraph-item--active': activeIndex === index }"
        type="button"
        @click="$emit('select', index)"
      >
        <span class="paragraph-index">{{ String(index + 1).padStart(2, "0") }}</span>
        <span class="paragraph-text">{{ paragraph.text }}</span>
        <span class="paragraph-time">预计 {{ paragraph.estimatedDuration }} 秒</span>
      </button>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import type { Paragraph, VoiceStudioStatus } from "@/stores/voice-studio";

defineProps<{
  activeIndex: number;
  errorMessage: string | null;
  paragraphs: Paragraph[];
  status: VoiceStudioStatus;
}>();

defineEmits<{
  select: [index: number];
}>();
</script>

<style scoped>
.voice-script-panel {
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
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.panel-heading strong {
  color: var(--brand-primary);
}

.paragraph-list {
  display: grid;
  gap: 10px;
  max-height: 100%;
  overflow: auto;
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
  transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
}

.paragraph-item:hover,
.paragraph-item--active {
  border-color: var(--brand-primary);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.paragraph-item:hover {
  transform: translateY(-1px);
}

.paragraph-index {
  color: var(--brand-primary);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  font-weight: 700;
}

.paragraph-text {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.paragraph-time {
  color: var(--text-muted);
  font-size: 12px;
}

.state {
  padding: 28px 16px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.state--error {
  color: var(--danger, #dc2626);
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
