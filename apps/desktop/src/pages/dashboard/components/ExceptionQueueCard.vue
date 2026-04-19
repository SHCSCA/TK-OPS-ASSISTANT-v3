<template>
  <Card class="exception-queue-card">
    <div class="exception-queue-card__header">
      <h3 class="exception-queue-card__title">{{ title }}</h3>
      <Chip :variant="badgeTone" size="sm">{{ badgeCount }}</Chip>
    </div>

    <div v-if="items.length === 0" class="exception-queue-card__empty">
      <span class="material-symbols-outlined">check_circle</span>
      <p>{{ emptyMessage }}</p>
    </div>

    <transition-group v-else name="queue-list" tag="ul" class="exception-queue-card__list">
      <li v-for="item in items.slice(0, 4)" :key="item.id" class="list-item">
        <span class="list-item__icon" :class="`is-${item.tone}`">
          <span class="material-symbols-outlined">{{ item.icon }}</span>
        </span>
        <span class="list-item__text" :title="item.title">{{ item.title }}</span>
        <span v-if="item.meta" class="list-item__meta">{{ item.meta }}</span>
      </li>
    </transition-group>

    <div class="exception-queue-card__footer" v-if="items.length > 4">
      <button class="view-more-btn">查看全部 ({{ items.length }})</button>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

export type ExceptionItem = {
  id: string;
  icon: string;
  title: string;
  meta?: string;
  tone: "neutral" | "brand" | "success" | "warning" | "danger" | "info";
};

const props = defineProps<{
  title: string;
  badgeCount: number;
  badgeTone: "neutral" | "brand" | "success" | "warning" | "danger" | "info";
  emptyMessage: string;
  items: ExceptionItem[];
}>();
</script>

<style scoped>
.exception-queue-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.exception-queue-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.exception-queue-card__title {
  font: var(--font-title-md);
  letter-spacing: var(--ls-title-md);
  color: var(--color-text-primary);
  margin: 0;
}

.exception-queue-card__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex: 1;
  color: var(--color-text-tertiary);
  text-align: center;
  min-height: 120px;
}

.exception-queue-card__empty .material-symbols-outlined {
  font-size: 32px;
  opacity: 0.5;
}

.exception-queue-card__empty p {
  margin: 0;
  font: var(--font-body-sm);
  letter-spacing: var(--ls-body-sm);
}

.exception-queue-card__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  background: var(--color-bg-canvas);
  border: 1px solid transparent;
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.list-item:hover {
  background: var(--color-bg-hover);
}

.list-item__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.list-item__icon .material-symbols-outlined {
  font-size: 18px;
}

.list-item__icon.is-danger { color: var(--color-danger); }
.list-item__icon.is-warning { color: var(--color-warning); }
.list-item__icon.is-brand { color: var(--color-brand-primary); }
.list-item__icon.is-success { color: var(--color-success); }
.list-item__icon.is-info { color: var(--color-info); }
.list-item__icon.is-neutral { color: var(--color-text-tertiary); }

.list-item__text {
  flex: 1;
  min-width: 0;
  font: var(--font-body-sm);
  letter-spacing: var(--ls-body-sm);
  color: var(--color-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.list-item__meta {
  flex-shrink: 0;
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  margin-top: 3px;
  white-space: nowrap;
}

.exception-queue-card__footer {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
  text-align: center;
}

.view-more-btn {
  background: transparent;
  border: none;
  color: var(--color-brand-primary);
  font: var(--font-caption);
  font-weight: 600;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.view-more-btn:hover {
  background: var(--color-bg-hover);
}

.queue-list-enter-active,
.queue-list-leave-active {
  transition: all var(--motion-fast) var(--ease-spring);
}
.queue-list-enter-from,
.queue-list-leave-to {
  opacity: 0;
  transform: translateX(-16px);
}
</style>
