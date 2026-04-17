<template>
  <div class="detail-context">
    <header class="detail-context__header">
      <div class="detail-context__header-copy">
        <p v-if="context.eyebrow" class="detail-context__eyebrow">{{ context.eyebrow }}</p>
        <div class="detail-context__title-row">
          <span v-if="context.icon" class="material-symbols-outlined detail-context__title-icon">{{ context.icon }}</span>
          <h2>{{ context.title }}</h2>
          <Chip v-if="context.badge" :tone="context.badge.tone ?? 'neutral'" size="sm">{{ context.badge.label }}</Chip>
        </div>
        <p v-if="context.description" class="detail-context__description">{{ context.description }}</p>
      </div>

      <button v-if="closable" class="detail-context__close" type="button" aria-label="关闭详情面板" @click="$emit('close')">
        <span class="material-symbols-outlined">close</span>
      </button>
    </header>

    <section v-if="context.metrics?.length" class="detail-context__metrics">
      <article v-for="metric in context.metrics" :key="metric.id" class="detail-context__metric">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small v-if="metric.hint">{{ metric.hint }}</small>
      </article>
    </section>

    <section v-for="section in context.sections" :key="section.id" class="detail-context__section">
      <div class="detail-context__section-header">
        <h3>{{ section.title }}</h3>
        <p v-if="section.description">{{ section.description }}</p>
      </div>

      <div v-if="section.fields?.length" class="detail-context__fields">
        <div v-for="field in section.fields" :key="field.id" class="detail-context__field">
          <span>{{ field.label }}</span>
          <strong :class="{ 'is-mono': field.mono, 'is-multiline': field.multiline }">{{ field.value }}</strong>
          <small v-if="field.hint">{{ field.hint }}</small>
        </div>
      </div>

      <ul v-else-if="section.items?.length" class="detail-context__items">
        <li v-for="item in section.items" :key="item.id" class="detail-context__item" :data-tone="item.tone || 'neutral'">
          <span v-if="item.icon" class="material-symbols-outlined detail-context__item-icon">{{ item.icon }}</span>
          <div class="detail-context__item-copy">
            <strong>{{ item.title }}</strong>
            <span v-if="item.description">{{ item.description }}</span>
          </div>
          <small v-if="item.meta">{{ item.meta }}</small>
        </li>
      </ul>

      <p v-else class="detail-context__empty">{{ section.emptyLabel || "当前没有可展示的上下文。" }}</p>
    </section>

    <footer v-if="context.actions?.length" class="detail-context__footer">
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
    case "danger":
      return "danger";
    case "brand":
      return "ai";
    default:
      return "secondary";
  }
}
</script>

<style scoped>
.detail-context {
  display: grid;
  gap: var(--space-4);
}

.detail-context__header {
  align-items: flex-start;
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
}

.detail-context__header-copy {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.detail-context__eyebrow {
  color: var(--color-text-tertiary);
  font-size: var(--font-caption);
  margin: 0;
}

.detail-context__title-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.detail-context__title-icon {
  color: var(--color-brand-primary);
  font-size: 18px;
}

.detail-context__title-row h2 {
  font-size: var(--font-title-lg);
  line-height: var(--line-title-lg);
  margin: 0;
}

.detail-context__description {
  color: var(--color-text-secondary);
  line-height: var(--line-body-sm);
  margin: 0;
}

.detail-context__close {
  align-items: center;
  background: transparent;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.detail-context__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.detail-context__metrics {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-context__metric,
.detail-context__field,
.detail-context__item {
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

.detail-context__metric {
  display: grid;
  gap: 4px;
  padding: var(--space-3);
}

.detail-context__metric span,
.detail-context__field span,
.detail-context__section-header p,
.detail-context__empty,
.detail-context__item small,
.detail-context__field small {
  color: var(--color-text-tertiary);
  font-size: var(--font-caption);
}

.detail-context__metric strong {
  font-size: var(--font-title-md);
}

.detail-context__section {
  display: grid;
  gap: var(--space-3);
}

.detail-context__section-header {
  display: grid;
  gap: 4px;
}

.detail-context__section-header h3 {
  font-size: var(--font-title-sm);
  margin: 0;
}

.detail-context__section-header p {
  margin: 0;
}

.detail-context__fields,
.detail-context__items {
  display: grid;
  gap: var(--space-2);
}

.detail-context__field {
  display: grid;
  gap: 4px;
  padding: var(--space-3);
}

.detail-context__field strong {
  color: var(--color-text-primary);
  font-size: var(--font-body-sm);
  line-height: var(--line-body-sm);
}

.detail-context__field strong.is-mono {
  font-family: var(--font-family-mono);
  word-break: break-all;
}

.detail-context__field strong.is-multiline {
  white-space: pre-wrap;
}

.detail-context__items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.detail-context__item {
  align-items: center;
  display: grid;
  gap: var(--space-3);
  grid-template-columns: auto minmax(0, 1fr) auto;
  padding: var(--space-3);
}

.detail-context__item[data-tone="brand"] {
  border-color: color-mix(in srgb, var(--color-brand-primary) 24%, var(--color-border-default));
}

.detail-context__item-icon {
  color: var(--color-brand-primary);
  font-size: 18px;
}

.detail-context__item-copy {
  display: grid;
  gap: 2px;
}

.detail-context__item-copy strong {
  color: var(--color-text-primary);
  font-size: var(--font-body-sm);
}

.detail-context__item-copy span {
  color: var(--color-text-secondary);
  font-size: var(--font-caption);
  line-height: var(--line-caption);
}

.detail-context__empty {
  background: var(--color-bg-muted);
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-md);
  margin: 0;
  padding: var(--space-3);
}

.detail-context__footer {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

@media (max-width: 1100px) {
  .detail-context__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
