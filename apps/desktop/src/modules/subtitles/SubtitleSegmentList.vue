<template>
  <section class="subtitle-segment-list">
    <header class="panel-heading">
      <span>字幕段落</span>
      <strong>{{ segments.length }}</strong>
    </header>

    <div v-if="status === 'loading'" class="state state--muted">
      正在读取脚本和字幕版本。
    </div>
    <div v-else-if="errorMessage" class="state state--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="segments.length === 0" class="state state--muted">
      请先在脚本与选题中心创建内容，或生成字幕草稿。
    </div>

    <TransitionGroup v-else name="subtitle-list" tag="div" class="segment-list">
      <article
        v-for="segment in segments"
        :key="segment.segmentIndex"
        class="segment-item"
        :class="{ 'segment-item--active': activeIndex === segment.segmentIndex }"
        @click="$emit('select', segment.segmentIndex)"
      >
        <div class="segment-head">
          <span>{{ String(segment.segmentIndex + 1).padStart(2, "0") }}</span>
          <small>{{ timeLabel(segment.startMs, segment.endMs) }}</small>
        </div>
        <textarea
          :value="segment.text"
          rows="3"
          @click.stop
          @input="
            $emit('update-segment', segment.segmentIndex, {
              text: ($event.target as HTMLTextAreaElement).value
            })
          "
        />
      </article>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import type { SubtitleAlignmentStatus } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto } from "@/types/runtime";

defineProps<{
  activeIndex: number;
  errorMessage: string | null;
  segments: SubtitleSegmentDto[];
  status: SubtitleAlignmentStatus;
}>();

defineEmits<{
  select: [index: number];
  "update-segment": [index: number, patch: Partial<SubtitleSegmentDto>];
}>();

function timeLabel(startMs: number | null, endMs: number | null): string {
  if (startMs === null || endMs === null) return "待对齐";
  return `${formatMs(startMs)} -> ${formatMs(endMs)}`;
}

function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const millis = ms % 1000;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}
</script>

<style scoped>
.subtitle-segment-list {
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

.segment-list {
  display: grid;
  gap: 10px;
  max-height: 100%;
  overflow: auto;
  padding: 12px;
}

.segment-item {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
}

.segment-item:hover,
.segment-item--active {
  border-color: var(--brand-primary);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.segment-item:hover {
  transform: translateY(-1px);
}

.segment-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.segment-head span {
  color: var(--brand-primary);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  font-weight: 800;
}

.segment-head small {
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11px;
}

textarea {
  min-height: 72px;
  resize: vertical;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-base);
  color: var(--text-primary);
  font: inherit;
  line-height: 1.6;
  outline: none;
  padding: 10px;
}

textarea:focus {
  border-color: var(--brand-primary);
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

.subtitle-list-enter-active,
.subtitle-list-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.subtitle-list-enter-from,
.subtitle-list-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@media (prefers-reduced-motion: reduce) {
  .segment-item,
  .subtitle-list-enter-active,
  .subtitle-list-leave-active {
    transition: none;
  }

  .segment-item:hover {
    transform: none;
  }
}
</style>
