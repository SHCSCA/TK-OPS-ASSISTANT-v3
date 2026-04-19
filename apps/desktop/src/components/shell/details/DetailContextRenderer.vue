<template>
  <div class="detail-context-renderer">
    <!-- Header -->
    <header class="detail-header">
      <div class="detail-header__content">
        <p v-if="context.eyebrow" class="detail-header__eyebrow">{{ context.eyebrow }}</p>
        <div class="detail-header__title-row">
          <span v-if="context.icon" class="material-symbols-outlined detail-header__icon">{{ context.icon }}</span>
          <h2 class="detail-header__title">{{ context.title }}</h2>
          <Chip v-if="context.badge" :variant="context.badge.tone ?? 'default'" size="sm">{{ context.badge.label }}</Chip>
        </div>
      </div>
      <button v-if="closable" class="detail-header__close" aria-label="关闭详情面板" @click="$emit('close')">
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <div class="detail-scroll-area">
      <!-- Metric Strip -->
      <div v-if="context.metrics?.length" class="detail-metrics">
        <div v-for="metric in context.metrics" :key="metric.id" class="detail-metric">
          <span class="detail-metric__label">{{ metric.label }}</span>
          <strong class="detail-metric__value">{{ metric.value }}</strong>
        </div>
      </div>

      <!-- Sections -->
      <section v-for="section in context.sections" :key="section.id" class="detail-section">
        <h3 class="detail-section__title">{{ section.title }}</h3>
        <p v-if="section.description" class="detail-section__description">{{ section.description }}</p>

        <!-- Empty State -->
        <div v-if="!section.fields?.length && !section.items?.length" class="detail-empty">
          <span v-if="section.emptyIcon" class="material-symbols-outlined detail-empty__icon">{{ section.emptyIcon }}</span>
          {{ section.emptyLabel || "当前没有可展示的上下文。" }}
        </div>

        <!-- Fields -->
        <div v-if="section.fields?.length" class="detail-fields-group">
          <div v-for="field in section.fields" :key="field.id" class="detail-field">
            <span class="detail-field__label">{{ field.label }}</span>
            <span 
              class="detail-field__value" 
              :data-mono="String(field.mono)"
              :style="field.multiline ? { whiteSpace: 'pre-wrap', textAlign: 'left', flex: 1 } : {}"
            >
              {{ field.value }}
            </span>
          </div>
        </div>

        <!-- Items -->
        <div v-if="section.items?.length" class="detail-items-group">
          <div v-for="item in section.items" :key="item.id" class="detail-item">
            <span v-if="item.icon" class="material-symbols-outlined detail-item__icon" :data-tone="item.tone">{{ item.icon }}</span>
            <div class="detail-item__body">
              <div class="detail-item__title">{{ item.title }}</div>
              <div v-if="item.description" class="detail-item__description">{{ item.description }}</div>
            </div>
            <span v-if="item.meta" class="detail-item__meta">{{ item.meta }}</span>
          </div>
        </div>
      </section>
    </div>

    <!-- Actions -->
    <footer v-if="context.actions?.length" class="detail-actions">
      <Button
        v-for="action in context.actions"
        :key="action.id"
        :disabled="action.disabled"
        :variant="mapActionVariant(action.tone)"
        size="sm"
      >
        <template v-if="action.icon" #leading>
          <span class="material-symbols-outlined">{{ action.icon }}</span>
        </template>
        {{ action.label }}
      </Button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import Button from "@/components/ui/Button/Button.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import type { DetailContext, DetailContextTone } from "@/stores/shell-ui";

defineProps<{
  closable?: boolean;
  context: DetailContext;
}>();

defineEmits<{
  close: [];
}>();

function mapActionVariant(tone: DetailContextTone | undefined) {
  switch (tone) {
    case "danger": return "danger";
    case "brand": return "ai";
    case "neutral": return "ghost";
    default: return "secondary";
  }
}
</script>

<style scoped>
.detail-context-renderer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding-bottom: var(--space-6);
}

/* Header */
.detail-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
}
.detail-header__content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 2px;
  justify-content: center;
}
.detail-header__eyebrow {
  margin: 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.detail-header__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.detail-header__icon {
  font-size: 20px;
  color: var(--color-brand-primary);
}
.detail-header__title {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-header__close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
  flex-shrink: 0;
  padding: 0;
}
.detail-header__close .material-symbols-outlined {
  font-size: 18px;
}
.detail-header__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

/* Metric Strip */
.detail-metrics {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-metric {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.detail-metric__value {
  font: var(--font-title-lg);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-metric__label {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

/* Section */
.detail-section {
  padding: var(--space-4) var(--space-4) 0;
}
.detail-section__title {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.detail-section__description {
  margin: 0 0 var(--space-3) 0;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}

/* Empty State */
.detail-empty {
  text-align: center;
  padding: var(--space-10) var(--space-6);
  color: var(--color-text-tertiary);
  font: var(--font-body-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.detail-empty__icon {
  font-size: 40px;
  margin-bottom: var(--space-4);
  opacity: 0.4;
}

/* Fields */
.detail-fields-group {
  display: flex;
  flex-direction: column;
}
.detail-field {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-subtle);
  gap: var(--space-4);
}
.detail-field:last-child {
  border-bottom: none;
}
.detail-field__label {
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  width: 100px;
}
.detail-field__value {
  font: var(--font-body-md);
  color: var(--color-text-primary);
  text-align: right;
  word-break: break-all;
}
.detail-field__value[data-mono="true"] {
  font-family: var(--font-family-mono);
  font-size: 12px;
}

/* Items */
.detail-items-group {
  display: flex;
  flex-direction: column;
}
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-subtle);
}
.detail-item:last-child {
  border-bottom: none;
}
.detail-item__icon {
  font-size: 18px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  margin-top: 1px;
}
.detail-item__icon[data-tone="brand"] { color: var(--color-brand-primary); }
.detail-item__icon[data-tone="success"] { color: var(--color-success); }
.detail-item__icon[data-tone="danger"] { color: var(--color-danger); }
.detail-item__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.detail-item__title {
  font: var(--font-body-md);
  color: var(--color-text-primary);
}
.detail-item__description {
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}
.detail-item__meta {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

/* Bottom Actions */
.detail-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  height: 56px;
  padding: 0 var(--space-4);
  background: var(--color-bg-surface);
  border-top: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
  z-index: 10;
}
</style>