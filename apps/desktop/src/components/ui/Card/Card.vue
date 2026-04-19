<template>
  <component
    :is="as"
    class="ui-card"
    :data-interactive="String(interactive)"
    :data-selected="String(selected)"
    :class="{ 'is-padded': padded }"
    v-bind="$attrs"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    as?: string;
    interactive?: boolean;
    padded?: boolean;
    selected?: boolean;
  }>(),
  {
    as: "div",
    interactive: false,
    padded: true,
    selected: false
  }
);
</script>

<style scoped>
.ui-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  position: relative;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring),
    border-color var(--motion-fast) var(--ease-standard);
  will-change: transform;
}

.ui-card.is-padded {
  padding: var(--space-6);
}

/* Hover（可交互卡片才启用） */
.ui-card[data-interactive="true"] {
  cursor: pointer;
}

.ui-card[data-interactive="true"]:hover {
  border-color: var(--color-border-default);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

/* Active */
.ui-card[data-interactive="true"]:active {
  transform: translateY(0);
  transition-duration: var(--motion-instant);
}

/* Selected */
.ui-card[data-selected="true"] {
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary), var(--shadow-md);
  z-index: 1; /* Lift selected cards above siblings if in a grid */
}

/* Ensure focus-visible is distinct for accessibility */
.ui-card[data-interactive="true"]:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
</style>
