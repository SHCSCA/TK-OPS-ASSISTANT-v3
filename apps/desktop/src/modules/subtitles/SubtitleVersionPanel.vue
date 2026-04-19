<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">字幕版本</span>
        <strong>{{ tracks.length }} 条记录</strong>
      </div>
      <span class="panel-heading__chip" :data-state="status">{{ statusLabel }}</span>
    </header>

    <div v-if="status === 'loading'" class="state-surface">
      <strong>正在读取字幕版本。</strong>
      <p>{{ stateMessage }}</p>
    </div>
    <div v-else-if="status === 'error'" class="state-surface state-surface--error">
      <strong>字幕版本读取失败。</strong>
      <p>{{ errorMessage || stateMessage }}</p>
    </div>
    <div v-else-if="tracks.length === 0" class="state-surface state-surface--empty">
      <strong>暂无字幕版本。</strong>
      <p>{{ stateMessage }}</p>
    </div>

    <TransitionGroup v-else name="subtitle-version" tag="div" class="version-list">
      <article
        v-for="track in tracks"
        :key="track.id"
        class="version-item"
        :class="{ 'version-item--active': selectedTrackId === track.id }"
        @click="$emit('select', track.id)"
      >
        <div class="version-head">
          <div>
            <strong>{{ track.language }}</strong>
            <p>{{ track.source }} · {{ track.timelineId ?? "无时间线绑定" }}</p>
          </div>
          <span class="version-state" :data-state="track.status">{{ statusText(track.status) }}</span>
        </div>
        <dl class="version-meta">
          <div>
            <dt>段落数</dt>
            <dd>{{ track.segments.length }}</dd>
          </div>
          <div>
            <dt>样式</dt>
            <dd>{{ track.style.preset }}</dd>
          </div>
        </dl>
        <button class="delete-button" type="button" @click.stop="confirmDelete(track.id)">
          删除
        </button>
      </article>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { SubtitleTrackDto, SubtitleTrackStatus } from "@/types/runtime";
import type { SubtitleAlignmentStatus } from "@/stores/subtitle-alignment";

const props = defineProps<{
  errorMessage: string | null;
  selectedTrackId: string | null;
  stateMessage: string;
  status: SubtitleAlignmentStatus;
  tracks: SubtitleTrackDto[];
}>();

const emit = defineEmits<{
  delete: [trackId: string];
  select: [trackId: string];
}>();

const statusLabel = computed(() => {
  if (props.status === "loading") return "读取中";
  if (props.status === "error") return "错误";
  if (props.status === "blocked") return "阻断";
  if (props.tracks.length === 0) return "空态";
  return "可用";
});

function statusText(status: SubtitleTrackStatus): string {
  if (status === "blocked") return "阻断";
  if (status === "ready") return "可用";
  if (status === "aligning") return "对齐中";
  return "错误";
}

function confirmDelete(trackId: string): void {
  if (window.confirm("确认删除这个字幕版本吗？")) {
    emit("delete", trackId);
  }
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
  color: var(--text-primary);
  font-size: 14px;
}

.panel-heading__chip,
.version-state {
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

.version-state[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 28%, transparent);
  color: var(--brand-primary);
}

.version-state[data-state="blocked"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.version-state[data-state="error"] {
  border-color: color-mix(in srgb, var(--danger) 28%, transparent);
  color: var(--danger);
}

.version-list {
  display: grid;
  gap: 8px;
  padding: 12px;
}

.version-item {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    transform 160ms ease,
    background-color 160ms ease;
}

.version-item:hover,
.version-item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 40%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.version-item:hover {
  transform: translateY(-1px);
}

.version-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.version-head div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.version-head strong {
  color: var(--text-primary);
  font-size: 14px;
}

.version-head p,
.version-meta dd {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.version-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.version-meta div {
  display: grid;
  gap: 4px;
}

.version-meta dt {
  color: var(--text-tertiary);
  font-size: 11px;
}

.delete-button {
  justify-self: start;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  padding: 4px 9px;
}

.delete-button:hover {
  border-color: var(--danger);
  color: var(--danger);
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

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.subtitle-version-enter-active,
.subtitle-version-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.subtitle-version-enter-from,
.subtitle-version-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

/* Reduced Motion 降级由 :root[data-reduced-motion="true"] 的 --motion-* 变量统一控制 */
</style>
