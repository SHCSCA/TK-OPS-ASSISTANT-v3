<template>
  <aside class="settings-section-rail">
    <p class="detail-panel__label">工作分区</p>
    <div class="settings-section-rail__list">
      <button
        v-for="item in items"
        :key="item.id"
        class="settings-section-rail__item"
        :class="{ 'settings-section-rail__item--active': item.id === currentSection }"
        type="button"
        :aria-label="`${item.label}：${item.summary}`"
        :data-section="item.id"
        :title="item.summary"
        @click="$emit('select', item.id)"
      >
        <strong>{{ item.label }}</strong>
        <span>{{ item.summary }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
type SettingsSectionId = "system" | "provider" | "capability" | "diagnostics";

defineProps<{
  currentSection: SettingsSectionId;
}>();

defineEmits<{
  (e: "select", section: SettingsSectionId): void;
}>();

const items: Array<{ id: SettingsSectionId; label: string; summary: string }> = [
  {
    id: "system",
    label: "系统总线",
    summary: "Runtime、路径、日志与默认 AI 项"
  },
  {
    id: "provider",
    label: "Provider 与模型",
    summary: "Provider 注册表、模型目录和连接凭据"
  },
  {
    id: "capability",
    label: "能力矩阵",
    summary: "能力绑定、默认模型和提示词策略"
  },
  {
    id: "diagnostics",
    label: "诊断工作台",
    summary: "错误、依赖和系统可用性"
  }
];
</script>

<style scoped>
.settings-section-rail {
  display: grid;
  align-content: start;
  align-self: start;
  gap: var(--space-3);
  min-height: auto;
  padding: var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-secondary) 94%, transparent);
}

.settings-section-rail .detail-panel__label {
  margin: 0;
}

.settings-section-rail__list {
  display: grid;
  gap: var(--space-2);
}

.settings-section-rail__item {
  display: flex;
  align-items: center;
  min-height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
}

.settings-section-rail__item strong {
  font: var(--font-title-sm);
  letter-spacing: 0;
}

.settings-section-rail__item span {
  display: none;
}

.settings-section-rail__item:hover,
.settings-section-rail__item--active {
  border-color: color-mix(in srgb, var(--brand-primary) 34%, var(--border-default));
  background: color-mix(in srgb, var(--brand-primary) 10%, var(--surface-tertiary));
  transform: translateX(2px);
}

@media (max-width: 1120px) {
  .settings-section-rail__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .settings-section-rail__list {
    grid-template-columns: 1fr;
  }
}
</style>
