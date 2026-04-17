<template>
  <label class="ui-dropdown">
    <span v-if="label" class="ui-dropdown__label">{{ label }}</span>
    <div class="ui-dropdown__control">
      <select class="ui-dropdown__select" :value="modelValue" v-bind="$attrs" @change="emitValue">
        <option v-for="option in options" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
      <span class="material-symbols-outlined ui-dropdown__icon">expand_more</span>
    </div>
  </label>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label?: string;
    modelValue: string;
    options: Array<{ label: string; value: string }>;
  }>(),
  {
    label: ""
  }
);

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

function emitValue(event: Event) {
  emit("update:modelValue", (event.target as HTMLSelectElement).value);
}
</script>

<style scoped>
.ui-dropdown {
  display: grid;
  gap: var(--space-2);
}

.ui-dropdown__label {
  color: var(--color-text-secondary);
  font-size: var(--font-caption);
  font-weight: 600;
}

.ui-dropdown__control {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  display: flex;
  min-height: 36px;
  overflow: hidden;
  padding: 0 12px;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.ui-dropdown__control:focus-within {
  background: var(--color-bg-surface);
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-brand-primary) 20%, transparent);
}

.ui-dropdown__select {
  appearance: none;
  background: transparent;
  border: 0;
  color: var(--color-text-primary);
  flex: 1;
  font: inherit;
  min-width: 0;
  outline: none;
}

.ui-dropdown__icon {
  color: var(--color-text-tertiary);
  font-size: 18px;
}
</style>
