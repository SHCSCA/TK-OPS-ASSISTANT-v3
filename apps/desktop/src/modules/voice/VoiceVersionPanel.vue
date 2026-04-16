<template>
  <section class="voice-version-panel">
    <header class="panel-heading">
      <span>配音版本</span>
      <small>{{ tracks.length }}</small>
    </header>

    <div v-if="tracks.length === 0" class="empty-text">
      暂无配音版本，生成后会在这里保留可追溯记录。
    </div>

    <TransitionGroup v-else name="voice-version" tag="div" class="version-list">
      <article
        v-for="track in tracks"
        :key="track.id"
        class="version-item"
        :class="{ 'version-item--active': selectedTrackId === track.id }"
        @click="$emit('select', track.id)"
      >
        <div class="version-head">
          <strong>{{ track.voiceName }}</strong>
          <span>{{ statusText(track.status) }}</span>
        </div>
        <p>{{ track.segments.length }} 个脚本段落 · {{ track.provider || "未绑定 Provider" }}</p>
        <button class="delete-button" type="button" @click.stop="confirmDelete(track.id)">
          删除
        </button>
      </article>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import type { VoiceTrackDto, VoiceTrackStatus } from "@/types/runtime";

defineProps<{
  selectedTrackId: string | null;
  tracks: VoiceTrackDto[];
}>();

const emit = defineEmits<{
  delete: [trackId: string];
  select: [trackId: string];
}>();

function statusText(status: VoiceTrackStatus): string {
  if (status === "blocked") return "待配置";
  if (status === "ready") return "可用";
  if (status === "generating") return "生成中";
  return "失败";
}

function confirmDelete(trackId: string): void {
  if (window.confirm("确认删除这个配音版本吗？")) {
    emit("delete", trackId);
  }
}
</script>

<style scoped>
.voice-version-panel {
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
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.panel-heading small {
  color: var(--brand-primary);
}

.version-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  padding: 10px;
}

.version-item {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
  cursor: pointer;
  transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
}

.version-item:hover,
.version-item--active {
  border-color: var(--brand-primary);
  background: color-mix(in srgb, var(--brand-primary) 8%, var(--bg-card));
}

.version-item:hover {
  transform: translateY(-1px);
}

.version-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.version-head strong {
  color: var(--text-primary);
  font-size: 14px;
}

.version-head span {
  color: var(--brand-primary);
  font-size: 12px;
  white-space: nowrap;
}

.version-item p {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
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
  border-color: var(--danger, #dc2626);
  color: var(--danger, #dc2626);
}

.empty-text {
  padding: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
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

@media (prefers-reduced-motion: reduce) {
  .version-item,
  .voice-version-enter-active,
  .voice-version-leave-active {
    transition: none;
  }

  .version-item:hover {
    transform: none;
  }
}
</style>
