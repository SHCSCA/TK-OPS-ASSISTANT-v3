<template>
  <div class="ui-tab" role="tablist">
    <button
      v-for="option in options"
      :key="option.value"
      class="ui-tab__item"
      :class="{ 'is-active': option.value === modelValue }"
      role="tab"
      type="button"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string;
  options: Array<{ label: string; value: string }>;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();
</script>

<style scoped>
.ui-tab {
  align-items: center;
  border-bottom: 1px solid var(--color-border-subtle);
  display: inline-flex;
  gap: var(--space-4);
  min-width: 0;
}

.ui-tab__item {
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: var(--font-title-sm);
  font-weight: 600;
  height: 40px;
  margin-bottom: -1px;
  padding: 0 var(--space-3);
  transition:
    color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-default) var(--ease-spring);
}

.ui-tab__item:hover {
  color: var(--color-text-primary);
}

.ui-tab__item.is-active {
  border-color: var(--color-brand-primary);
  color: var(--color-text-primary);
}
</style>
