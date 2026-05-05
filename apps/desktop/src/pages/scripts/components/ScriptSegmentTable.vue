<template>
  <div class="script-segment-list" data-script-segment-table>
    <div
      v-for="(segment, index) in segments"
      :key="index"
      class="segment-card"
    >
      <div class="segment-card__head">
        <strong class="segment-card__id">{{ segment.id }}</strong>
        <span class="segment-card__time">{{ segment.time }}</span>
      </div>
      <div class="segment-card__goal">{{ segment.goal }}</div>
      <div v-if="segment.voiceover" class="segment-card__voice">{{ segment.voiceover }}</div>
    </div>
    <div v-if="segments.length === 0" class="empty-text">暂无分段数据。</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ScriptDocumentJson } from "@/modules/scripts/script-document-view-model";

const props = defineProps<{
  documentJson: ScriptDocumentJson;
}>();

type SegmentItem = {
  id: string;
  time: string;
  goal: string;
  voiceover: string;
};

const segments = computed<SegmentItem[]>(() => {
  const doc = props.documentJson;
  if (!doc || !Array.isArray(doc.segments)) return [];
  return doc.segments.map((seg: Record<string, unknown>, i: number) => ({
    id: String(seg.segmentId ?? `S${String(i + 1).padStart(2, "0")}`),
    time: String(seg.time ?? ""),
    goal: String(seg.goal ?? ""),
    voiceover: String(seg.voiceover ?? "").slice(0, 60)
  }));
});
</script>

<style scoped>
.script-segment-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.segment-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background var(--motion-fast) var(--ease-standard);
}

.segment-card:hover {
  background: var(--color-bg-hover);
}

.segment-card:last-child {
  border-bottom: none;
}

.segment-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.segment-card__id {
  font: var(--font-title-sm);
  color: var(--color-brand-primary);
  white-space: nowrap;
}

.segment-card__time {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.segment-card__goal {
  font: var(--font-body-sm);
  color: var(--color-text-primary);
  line-height: 1.45;
}

.segment-card__voice {
  font: var(--font-caption);
  color: var(--color-text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-text {
  padding: var(--space-4);
  text-align: center;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}
</style>
