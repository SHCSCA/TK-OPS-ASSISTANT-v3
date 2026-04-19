<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">字幕段草稿</span>
        <strong>{{ segments.length }} 段</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div v-if="status === 'loading'" class="state-surface">
      <strong>正在读取脚本和字幕版本。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-else-if="status === 'error'" class="state-surface state-surface--error">
      <strong>字幕段读取失败。</strong>
      <p>{{ errorMessage || stateMessage }}</p>
    </div>
    <div v-else-if="segments.length === 0" class="state-surface state-surface--empty">
      <strong>字幕段为空。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-if="status === 'blocked' && segments.length > 0" class="state-surface state-surface--blocked">
      <strong>字幕草稿已写入，但对齐能力被阻断。</strong>
      <p>{{ stateMessage }}</p>
    </div>

    <TransitionGroup v-if="segments.length > 0" name="subtitle-list" tag="div" class="segment-list">
      <article
        v-for="segment in segments"
        :key="segment.segmentIndex"
        class="segment-item"
        :class="{ 'segment-item--active': activeIndex === segment.segmentIndex }"
        @click="$emit('select', segment.segmentIndex)"
      >
        <div class="segment-head">
          <div>
            <span>{{ String(segment.segmentIndex + 1).padStart(2, "0") }}</span>
            <small>{{ timeLabel(segment.startMs, segment.endMs) }}</small>
          </div>
          <span class="segment-lock" :data-state="segment.locked ? 'blocked' : 'ready'">
            {{ segment.locked ? "锁定" : "可改" }}
          </span>
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
        <div class="segment-meta">
          <span>置信度：{{ segment.confidence ?? "未接通" }}</span>
          <span>锁定：{{ segment.locked ? "是" : "否" }}</span>
        </div>
      </article>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SubtitleAlignmentStatus } from "@/stores/subtitle-alignment";
import type { SubtitleSegmentDto } from "@/types/runtime";

const props = defineProps<{
  activeIndex: number;
  errorMessage: string | null;
  segments: SubtitleSegmentDto[];
  stateMessage: string;
  status: SubtitleAlignmentStatus;
}>();

defineEmits<{
  select: [index: number];
  "update-segment": [index: number, patch: Partial<SubtitleSegmentDto>];
}>();

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "error") return "错误";
  if (props.status === "blocked") return "阻断";
  if (props.segments.length === 0) return "空态";
  return "可用";
});

function timeLabel(startMs: number | null, endMs: number | null): string {
  if (startMs === null || endMs === null) return "待对齐";
  return `${formatMs(startMs)} → ${formatMs(endMs)}`;
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

.panel-heading__chip,
.segment-lock {
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

.segment-lock[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 28%, transparent);
  color: var(--brand-primary);
}

.segment-lock[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.segment-list {
  display: grid;
  gap: 10px;
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
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-spring),
    background-color var(--motion-fast) var(--ease-standard);
}

.segment-item:hover,
.segment-item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 40%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.segment-item:hover {
  transform: translateY(-1px);
}

.segment-item:active {
  transform: scale(0.98);
}

.segment-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.segment-head > div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.segment-head span:first-child {
  color: var(--brand-primary);
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.segment-head small {
  color: var(--text-tertiary);
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

.segment-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.state-surface {
  display: grid;
  gap: 6px;
  padding: 16px;
  margin: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
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

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.subtitle-list-move,
.subtitle-list-enter-active,
.subtitle-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}

.subtitle-list-enter-from,
.subtitle-list-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.subtitle-list-leave-active {
  position: absolute;
}

/* Reduced Motion 降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
