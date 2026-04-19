<template>
  <div class="ui-input-wrapper">
    <label v-if="label" class="ui-input__label">{{ label }}</label>
    <div
      class="ui-input__control"
      :class="{
        'is-disabled': disabled,
        'is-textarea': multiline,
        'has-error': error
      }"
      :data-error="error ? 'true' : 'false'"
    >
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
    <div v-if="hint" class="ui-input__hint" :class="{ 'is-error': error }">
      {{ hint }}
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    disabled?: boolean;
    error?: boolean;
    hint?: string;
    label?: string;
    modelValue?: string;
    multiline?: boolean;
    placeholder?: string;
    rows?: number;
    type?: string;
  }>(),
  {
    disabled: false,
    error: false,
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
.ui-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.ui-input__label {
  color: var(--color-text-secondary);
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
}

.ui-input__control {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  display: flex;
  gap: var(--space-2);
  min-height: 36px;
  padding: 0 12px;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.ui-input__control:hover:not(.is-disabled) {
  background: var(--color-bg-surface);
}

.ui-input__control:focus-within:not(.is-disabled) {
  background: var(--color-bg-surface);
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 3px var(--color-brand-glow);
}

.ui-input__control[data-error="true"]:not(.is-disabled) {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-danger) 18%, transparent);
}

.ui-input__field {
  background: transparent;
  border: 0;
  color: var(--color-text-primary);
  flex: 1;
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  min-width: 0;
  outline: none;
  padding: 0;
  width: 100%;
}

.ui-input__field::placeholder {
  color: var(--color-text-tertiary);
}

.ui-input__field--textarea {
  min-height: 72px;
  padding: 8px 0;
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

.is-textarea {
  align-items: stretch;
}

.ui-input__control.is-disabled {
  background: var(--color-bg-muted);
  cursor: not-allowed;
}

.ui-input__control.is-disabled .ui-input__field,
.ui-input__control.is-disabled .ui-input__icon {
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.ui-input__hint {
  color: var(--color-text-secondary);
  font: var(--font-body-sm);
  letter-spacing: var(--ls-body-sm);
  margin-top: -2px;
}

.ui-input__hint.is-error {
  color: var(--color-danger);
}
</style>
