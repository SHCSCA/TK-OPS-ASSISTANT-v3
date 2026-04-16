<template>
  <section class="subtitle-timing-panel">
    <header class="panel-heading">
      <span>时间码校正</span>
      <small>{{ segment ? "当前段" : "未选择" }}</small>
    </header>

    <div v-if="!segment" class="empty-text">
      选择字幕段后，可手动填写毫秒级起止时间。无真实对齐时保持待对齐。
    </div>

    <div v-else class="timing-fields">
      <label>
        <span>开始毫秒</span>
        <input
          :value="segment.startMs ?? ''"
          inputmode="numeric"
          placeholder="待对齐"
          type="number"
          @input="updateNumber('startMs', $event)"
        />
      </label>
      <label>
        <span>结束毫秒</span>
        <input
          :value="segment.endMs ?? ''"
          inputmode="numeric"
          placeholder="待对齐"
          type="number"
          @input="updateNumber('endMs', $event)"
        />
      </label>
      <label class="lock-row">
        <input
          :checked="segment.locked"
          type="checkbox"
          @change="$emit('update-segment', { locked: ($event.target as HTMLInputElement).checked })"
        />
        <span>锁定此段，后续对齐不自动覆盖</span>
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SubtitleSegmentDto } from "@/types/runtime";

defineProps<{
  segment: SubtitleSegmentDto | null;
}>();

const emit = defineEmits<{
  "update-segment": [patch: Partial<SubtitleSegmentDto>];
}>();

function updateNumber(field: "startMs" | "endMs", event: Event): void {
  const value = (event.target as HTMLInputElement).value;
  emit("update-segment", { [field]: value === "" ? null : Number(value) });
}
</script>

<style scoped>
.subtitle-timing-panel {
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

.timing-fields {
  display: grid;
  gap: 10px;
  padding: 12px;
}

label {
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

input[type="number"] {
  height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-base);
  color: var(--text-primary);
  padding: 0 10px;
}

.lock-row {
  grid-template-columns: auto 1fr;
  align-items: center;
}

.empty-text {
  padding: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}
</style>
