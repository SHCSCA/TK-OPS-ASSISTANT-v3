<template>
  <section class="ui-card" :class="[`ui-card--${variant}`, { 'is-interactive': interactive }]" v-bind="$attrs">
    <slot />
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    interactive?: boolean;
    variant?: "default" | "muted" | "selected";
  }>(),
  {
    interactive: false,
    variant: "default"
  }
);
</script>

<style scoped>
.ui-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring),
    border-color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.ui-card--muted {
  background: var(--color-bg-muted);
  box-shadow: none;
}

.ui-card--selected {
  border-color: color-mix(in srgb, var(--color-brand-primary) 42%, var(--color-border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-brand-primary) 12%, transparent), var(--shadow-sm);
}

.is-interactive {
  cursor: pointer;
}

.is-interactive:hover {
  border-color: var(--color-border-default);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.is-interactive:active {
  transform: translateY(0);
}
</style>
