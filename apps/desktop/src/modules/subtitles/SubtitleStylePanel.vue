<template>
  <section class="subtitle-style-panel">
    <header class="panel-heading">
      <span>字幕样式</span>
      <small>{{ styleConfig.preset }}</small>
    </header>

    <div class="style-fields">
      <label>
        <span>字号</span>
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
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SubtitleStyleDto } from "@/types/runtime";

defineProps<{
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
.subtitle-style-panel {
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

.style-fields {
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

input,
select {
  height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-base);
  color: var(--text-primary);
  padding: 0 10px;
}
</style>
