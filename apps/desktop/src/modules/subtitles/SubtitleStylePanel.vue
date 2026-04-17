<template>
  <section class="panel-shell">
    <header class="panel-heading">
      <div>
        <span class="panel-heading__kicker">字幕样式</span>
        <strong>{{ styleConfig.preset }}</strong>
      </div>
      <span class="panel-heading__chip" :data-state="locked ? 'disabled' : 'ready'">
        {{ locked ? "锁定" : "可编辑" }}
      </span>
    </header>

    <div v-if="locked" class="state-surface state-surface--locked">
      <strong>样式面板已锁定。</strong>
      <p>{{ lockedReason }}</p>
    </div>

    <fieldset class="style-fields" :disabled="locked">
      <label>
        <span>字体大小</span>
        <input
          :value="styleConfig.fontSize"
          max="72"
          min="18"
          type="number"
          @input="updateFontSize"
        />
      </label>
      <label>
        <span>位置</span>
        <select
          :value="styleConfig.position"
          @change="
            $emit('update-style', {
              position: ($event.target as HTMLSelectElement).value as 'bottom' | 'center' | 'top'
            })
          "
        >
          <option value="bottom">底部</option>
          <option value="center">居中</option>
          <option value="top">顶部</option>
        </select>
      </label>
      <label>
        <span>文字颜色</span>
        <input
          :value="styleConfig.textColor"
          type="text"
          @input="$emit('update-style', { textColor: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <label>
        <span>背景色</span>
        <input
          :value="styleConfig.background"
          type="text"
          @input="$emit('update-style', { background: ($event.target as HTMLInputElement).value })"
        />
      </label>
    </fieldset>
  </section>
</template>

<script setup lang="ts">
import type { SubtitleStyleDto } from "@/types/runtime";

defineProps<{
  locked: boolean;
  lockedReason: string;
  styleConfig: SubtitleStyleDto;
}>();

const emit = defineEmits<{
  "update-style": [patch: Partial<SubtitleStyleDto>];
}>();

function updateFontSize(event: Event): void {
  emit("update-style", { fontSize: Number((event.target as HTMLInputElement).value) });
}
</script>

<style scoped>
.panel-shell {
  display: grid;
  gap: 14px;
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

.state-surface strong {
  font-size: 14px;
}

.state-surface p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.style-fields {
  display: grid;
  gap: 10px;
  padding: 0 16px 16px;
  margin: 0;
  border: 0;
}

label {
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

input,
select {
  height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-base);
  color: var(--text-primary);
  padding: 0 10px;
}

@media (prefers-reduced-motion: reduce) {
  input,
  select {
    transition: none;
  }
}
</style>
