<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">时间码校正</span>
        <strong>{{ segment ? `第 ${segment.segmentIndex + 1} 段` : "未选中" }}</strong>
      </div>
      <span class="panel-heading__chip" :data-state="locked ? 'disabled' : 'ready'">
        {{ locked ? "锁定" : "可编辑" }}
      </span>
    </header>

    <div v-if="locked" class="state-surface state-surface--locked">
      <strong>时间码面板已锁定。</strong>
      <p>{{ lockedReason }}</p>
    </div>

    <div v-else-if="!segment" class="state-surface state-surface--empty">
      <strong>还没有可编辑的字幕段。</strong>
      <p>选中一段字幕后，就可以手工填写毫秒级起止时间。</p>
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
        <span>锁定这一段，后续不会被自动覆盖</span>
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SubtitleSegmentDto } from "@/types/runtime";

defineProps<{
  locked: boolean;
  lockedReason: string;
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
.panel-shell {
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

.panel-heading__chip[data-state="disabled"] {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
  color: var(--warning);
}

.panel-heading__chip[data-state="ready"] {
  border-color: color-mix(in srgb, var(--brand-primary) 28%, transparent);
  color: var(--brand-primary);
}

.state-surface {
  display: grid;
  gap: 6px;
  margin: 0 16px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.state-surface--locked {
  border-color: color-mix(in srgb, var(--warning) 28%, transparent);
}

.state-surface--empty {
  border-color: color-mix(in srgb, var(--text-tertiary) 22%, transparent);
}

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.timing-fields {
  display: grid;
  gap: 10px;
  padding: 12px 16px 16px;
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
</style>
