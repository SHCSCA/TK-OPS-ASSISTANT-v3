<template>
  <nav class="settings-nav">
    <div v-for="(group, gIdx) in groups" :key="gIdx" class="nav-group">
      <div v-if="gIdx > 0" class="nav-divider" />
      <button
        v-for="item in group"
        :key="item.id"
        class="nav-item"
        :class="{ 'is-active': modelValue === item.id }"
        :data-section="item.id"
        @click="$emit('update:modelValue', item.id)"
      >
        <span class="material-symbols-outlined nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import type { SettingsSectionId } from "../types";

defineProps<{
  modelValue: SettingsSectionId;
}>();

defineEmits<{
  (e: "update:modelValue", value: SettingsSectionId): void;
}>();

const groups: Array<Array<{ id: SettingsSectionId; label: string; icon: string }>> = [
  [
    { id: "system", label: "系统总线", icon: "dns" },
    { id: "provider", label: "Provider 与模型", icon: "hub" },
    { id: "capability", label: "能力矩阵", icon: "account_tree" },
    { id: "prompt", label: "Prompt 模板", icon: "terminal" }
  ],
  [
    { id: "voice", label: "音色管理", icon: "record_voice_over" },
    { id: "subtitle", label: "字幕策略", icon: "subtitles" }
  ],
  [
    { id: "directory", label: "目录设置", icon: "folder_open" },
    { id: "cache", label: "缓存管理", icon: "cached" },
    { id: "logging", label: "运行日志", icon: "receipt_long" }
  ]
];
</script>

<style scoped>
.settings-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin: var(--space-2) var(--space-3);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-4);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font: var(--font-title-sm);
  cursor: pointer;
  text-align: left;
  transition: all var(--motion-fast) var(--ease-standard);
}

.nav-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.nav-item.is-active {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
}

.nav-icon {
  font-size: 18px;
}
</style>
