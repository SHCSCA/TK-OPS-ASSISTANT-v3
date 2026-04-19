<template>
  <div class="prompt-list-container">
    <header class="list-header">
      <p class="summary">为每项 AI 能力配置角色设定、系统 Prompt 和用户 Prompt 模板。</p>
    </header>

    <div class="prompt-accordion">
      <div 
        v-for="item in items" 
        :key="item.capabilityId" 
        class="prompt-item"
        :class="{ 'is-expanded': item.expanded }"
      >
        <div class="prompt-header" @click="$emit('toggle', item.capabilityId)">
          <div class="header-main">
            <span class="capability-name">{{ item.label }}</span>
            <div class="header-summary" v-if="!item.expanded">
              <span class="role-tag">{{ item.agentRole || "未设定角色" }}</span>
            </div>
          </div>
          <span class="material-symbols-outlined expand-icon">
            {{ item.expanded ? 'expand_less' : 'expand_more' }}
          </span>
        </div>

        <transition name="expand">
          <div v-if="item.expanded" class="prompt-content-wrapper">
            <PromptTemplateEditor
              :item="item"
              @update="$emit('update', $event)"
              @reset="$emit('reset', item.capabilityId)"
              @save="$emit('save', item.capabilityId)"
            />
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PromptEditorState } from "../types";
import PromptTemplateEditor from "./PromptTemplateEditor.vue";

defineProps<{
  items: PromptEditorState[];
}>();

defineEmits<{
  (e: "toggle", id: string): void;
  (e: "update", patch: Partial<PromptEditorState> & { capabilityId: string }): void;
  (e: "reset", id: string): void;
  (e: "save", id: string): void;
}>();
</script>

<style scoped>
.prompt-list-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.list-header {
  margin-bottom: var(--space-2);
}

.summary {
  font: var(--font-body-md);
  color: var(--color-text-secondary);
  margin: 0;
}

.prompt-accordion {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.prompt-item {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  overflow: hidden;
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.prompt-item.is-expanded {
  border-color: var(--color-brand-primary);
}

.prompt-header {
  padding: var(--space-4) var(--space-5);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  background: var(--color-bg-canvas);
}

.header-main {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
  min-width: 0;
}

.capability-name {
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.header-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
}

.role-tag {
  background: var(--color-bg-muted);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.expand-icon {
  color: var(--color-text-tertiary);
}

.prompt-content-wrapper {
  overflow: hidden;
}

.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease-in-out;
  max-height: 1000px;
}
.expand-enter-from, .expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
