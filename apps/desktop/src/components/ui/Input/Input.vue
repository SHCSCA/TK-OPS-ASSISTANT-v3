<template>
  <label class="ui-input" :class="{ 'is-disabled': disabled, 'is-textarea': multiline }">
    <span v-if="label" class="ui-input__label">{{ label }}</span>
    <div class="ui-input__control">
      <span v-if="$slots.leading" class="ui-input__icon">
        <slot name="leading" />
      </span>
      <textarea
        v-if="multiline"
        class="ui-input__field ui-input__field--textarea"
        :disabled="disabled"
        :placeholder="placeholder"
        :rows="rows"
        :value="modelValue"
        v-bind="$attrs"
        @input="emitValue"
      />
      <input
        v-else
        class="ui-input__field"
        :disabled="disabled"
        :placeholder="placeholder"
        :type="type"
        :value="modelValue"
        v-bind="$attrs"
        @input="emitValue"
      />
      <span v-if="$slots.trailing" class="ui-input__icon ui-input__icon--trailing">
        <slot name="trailing" />
      </span>
    </div>
  </label>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    disabled?: boolean;
    label?: string;
    modelValue?: string;
    multiline?: boolean;
    placeholder?: string;
    rows?: number;
    type?: string;
  }>(),
  {
    disabled: false,
    label: "",
    modelValue: "",
    multiline: false,
    placeholder: "",
    rows: 4,
    type: "text"
  }
);

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

function emitValue(event: Event) {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement;
  emit("update:modelValue", target.value);
}
</script>

<style scoped>
.ui-input {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}

.ui-input__label {
  color: var(--color-text-secondary);
  font-size: var(--font-caption);
  font-weight: 600;
  line-height: var(--line-caption);
}

.ui-input__control {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  display: flex;
  gap: var(--space-2);
  min-height: 36px;
  padding: 0 12px;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.ui-input__control:focus-within {
  background: var(--color-bg-surface);
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-brand-primary) 20%, transparent);
}

.ui-input__field {
  background: transparent;
  border: 0;
  color: var(--color-text-primary);
  flex: 1;
  font: inherit;
  line-height: var(--line-body-md);
  min-width: 0;
  outline: none;
  padding: 0;
}

.ui-input__field::placeholder {
  color: var(--color-text-tertiary);
}

.ui-input__field--textarea {
  min-height: 96px;
  padding: 10px 0;
  resize: vertical;
}

.ui-input__icon {
  color: var(--color-text-tertiary);
  display: inline-flex;
  font-size: 18px;
  line-height: 1;
}

.ui-input__icon--trailing {
  justify-content: flex-end;
}

.is-textarea .ui-input__control {
  align-items: stretch;
}

.is-disabled {
  opacity: 0.56;
}
</style>
