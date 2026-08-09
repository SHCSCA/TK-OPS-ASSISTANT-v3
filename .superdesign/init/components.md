# Superdesign 共享 UI 原语上下文

> 2026-07-19 原型覆盖：本轮设计目标是 `docs/prototypes/tk-ops-account-workspace/` 的 React PC 交互原型。复用现有 `AppSidebar`、`AccountSwitcher`、`TopBar`、`DetailPanel`、`PageSection`、按钮、状态标签与表格视觉；新增脚本选题、分镜规划、视频拆解、媒体工具向导与任务详情组件。生产端 Vue 组件只作为历史设计参照，不作为本轮实现目标。

## 技术识别

- Framework: Vue 3 + TypeScript + Vite
- Desktop shell: Tauri 2
- State / routing: Pinia + Vue Router
- Component library: 仓库自研 Vue UI 原语，无第三方组件库
- CSS approach: 原生 CSS、scoped CSS、CSS Variables 语义令牌，无 Tailwind

## Button

- File: `apps/desktop/src/components/ui/Button/Button.vue`
- Description: 统一按钮原语，覆盖主要、次要、幽灵与危险动作及动效反馈。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <button
    class="ui-button"
    :class="[
      `ui-button--${variant}`,
      `ui-button--${size}`,
      {
        'is-block': block,
        'is-disabled': disabled,
        'is-icon-only': iconOnly
      }
    ]"
    :data-state="running ? 'running' : 'idle'"
    :disabled="disabled"
    :type="type"
    v-bind="$attrs"
  >
    <span v-if="$slots.leading" class="ui-button__icon">
      <slot name="leading" />
    </span>
    <span v-if="!iconOnly" class="ui-button__label">
      <slot />
    </span>
    <span v-if="$slots.trailing && !iconOnly" class="ui-button__icon">
      <slot name="trailing" />
    </span>
  </button>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    block?: boolean;
    disabled?: boolean;
    iconOnly?: boolean;
    running?: boolean;
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit" | "reset";
    variant?: "primary" | "secondary" | "ghost" | "danger" | "ai";
  }>(),
  {
    block: false,
    disabled: false,
    iconOnly: false,
    running: false,
    size: "md",
    type: "button",
    variant: "secondary"
  }
);
</script>

<style scoped>
/* 基础属性 */
.ui-button {
  align-items: center;
  appearance: none;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: inline-flex;
  gap: var(--space-2);
  justify-content: center;
  min-width: 0;
  outline: none;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce),
    filter var(--motion-fast) var(--ease-standard);
  will-change: transform;
}

.ui-button__icon {
  align-items: center;
  display: inline-flex;
  font-size: 18px; /* Material symbols usually look good at 18/20px */
  line-height: 1;
}

.ui-button__label {
  white-space: nowrap;
}

/* 尺寸规范 */
.ui-button--sm {
  height: 32px;
  min-height: 32px;
  padding: 0 12px;
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
}
.ui-button--sm.is-icon-only {
  width: 32px;
  padding: 0;
}

.ui-button--md {
  height: 36px;
  padding: 0 16px;
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
}
.ui-button--md.is-icon-only {
  width: 36px;
  padding: 0;
}

.ui-button--lg {
  height: 44px;
  padding: 0 20px;
  font: var(--font-title-md);
  letter-spacing: var(--ls-title-md);
}
.ui-button--lg.is-icon-only {
  width: 44px;
  padding: 0;
}

/* Primary */
.ui-button--primary {
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
}
.ui-button--primary:hover:not(:disabled) {
  background: var(--color-brand-primary-hover);
  box-shadow: var(--shadow-glow-brand);
}
.ui-button--primary:active:not(:disabled) {
  background: var(--color-brand-primary-active);
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}
.ui-button--primary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--primary:disabled,
.ui-button--primary.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* Secondary */
.ui-button--secondary {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}
.ui-button--secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--color-border-strong);
}
.ui-button--secondary:active:not(:disabled) {
  background: var(--color-bg-active);
  transform: scale(0.98);
  transition-duration: var(--motion-instant);
}
.ui-button--secondary:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--secondary:disabled,
.ui-button--secondary.is-disabled {
  color: var(--color-text-tertiary);
  border-color: var(--color-border-subtle);
  cursor: not-allowed;
  transform: none;
}

/* AI */
.ui-button--ai {
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  background-position: 0% 50%;
  color: #FFFFFF;
  position: relative;
  overflow: hidden;
  transition:
    background-position var(--motion-default) var(--ease-standard),
    transform var(--motion-instant) var(--ease-bounce),
    box-shadow var(--motion-fast) var(--ease-standard);
}
.ui-button--ai:hover:not(:disabled) {
  background-position: 100% 50%;
  box-shadow: var(--shadow-glow-ai);
}
.ui-button--ai:active:not(:disabled) {
  transform: scale(0.98);
}
.ui-button--ai[data-state="running"]:not(:disabled) {
  animation: ai-flow var(--motion-flow) linear infinite;
  box-shadow: var(--shadow-glow-ai);
}
.ui-button--ai:focus-visible {
  outline: 2px solid var(--color-brand-secondary);
  outline-offset: 2px;
}
.ui-button--ai:disabled,
.ui-button--ai.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}
@keyframes ai-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}

/* Danger */
.ui-button--danger {
  background: var(--color-danger);
  color: #FFFFFF;
}
.ui-button--danger:hover:not(:disabled) {
  filter: brightness(1.1);
  box-shadow: 0 4px 12px rgba(255, 90, 99, 0.2);
}
.ui-button--danger:active:not(:disabled) {
  transform: scale(0.98);
  filter: brightness(0.95);
}
.ui-button--danger:focus-visible {
  outline: 2px solid var(--color-danger);
  outline-offset: 2px;
}
.ui-button--danger:disabled,
.ui-button--danger.is-disabled {
  background: var(--color-bg-muted);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}

/* Ghost */
.ui-button--ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.ui-button--ghost:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}
.ui-button--ghost:active:not(:disabled) {
  background: var(--color-bg-active);
  transform: scale(0.98);
}
.ui-button--ghost:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}
.ui-button--ghost:disabled,
.ui-button--ghost.is-disabled {
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  transform: none;
}

/* 其他辅助 */
.is-block {
  width: 100%;
}
</style>

```

## Card

- File: `apps/desktop/src/components/ui/Card/Card.vue`
- Description: 统一内容卡片容器。
- Key props: 以源码中的 `defineProps` 为准。

```vue
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

```

## Chip

- File: `apps/desktop/src/components/ui/Chip/Chip.vue`
- Description: 统一状态、筛选和语义标签。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <span
    class="ui-chip"
    :data-variant="variant"
    :class="{ 'is-clickable': clickable }"
    v-bind="$attrs"
  >
    <span v-if="$slots.icon || icon" class="ui-chip__icon">
      <slot name="icon">
        <span class="material-symbols-outlined">{{ icon }}</span>
      </slot>
    </span>
    <span class="ui-chip__label">
      <slot>{{ label }}</slot>
    </span>
    <button v-if="removable" class="ui-chip__remove" aria-label="移除标签" @click.stop="$emit('remove')">
      <span class="material-symbols-outlined">close</span>
    </button>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    clickable?: boolean;
    icon?: string;
    label?: string;
    removable?: boolean;
    variant?: "default" | "brand" | "success" | "warning" | "danger" | "info";
  }>(),
  {
    clickable: false,
    label: "",
    removable: false,
    variant: "default"
  }
);

defineEmits<{
  (e: "remove"): void;
}>();
</script>

<style scoped>
.ui-chip {
  align-items: center;
  background: var(--color-bg-muted);
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  display: inline-flex;
  font: var(--font-caption);
  gap: 6px;
  height: 22px;
  letter-spacing: var(--ls-caption);
  padding: 0 8px;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
  white-space: nowrap;
}

/* 变体: Default (已在基础类定义) */
.ui-chip[data-variant="default"] {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

/* 变体: Brand */
.ui-chip[data-variant="brand"] {
  background: var(--color-bg-active);
  color: var(--color-brand-primary);
}

/* 变体: Success */
.ui-chip[data-variant="success"] {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

/* 变体: Warning */
.ui-chip[data-variant="warning"] {
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
  color: var(--color-warning);
}

/* 变体: Danger */
.ui-chip[data-variant="danger"] {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

/* 变体: Info */
.ui-chip[data-variant="info"] {
  background: color-mix(in srgb, var(--color-info) 12%, transparent);
  color: var(--color-info);
}

/* 可交互悬停态 */
.ui-chip.is-clickable {
  cursor: pointer;
}

.ui-chip.is-clickable:hover {
  border-color: currentColor;
}

.ui-chip.is-clickable:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}

.ui-chip.is-clickable:active {
  transform: scale(0.96);
  transition-duration: var(--motion-haptic);
}

/* 图标 */
.ui-chip__icon {
  align-items: center;
  display: flex;
  font-size: 14px;
  line-height: 1;
}

.ui-chip__icon :deep(.material-symbols-outlined) {
  font-size: 14px;
}

.ui-chip__label {
  line-height: 1;
}

/* 移除按钮 — 视觉 16px 图标，点击区域扩大到 24px */
.ui-chip__remove {
  align-items: center;
  appearance: none;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  color: currentColor;
  cursor: pointer;
  display: flex;
  height: 24px;
  justify-content: center;
  margin: -4px -4px -4px -4px;
  opacity: 0.6;
  outline: none;
  padding: 0;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    opacity var(--motion-fast) var(--ease-standard);
  width: 24px;
}

.ui-chip__remove:hover {
  background: color-mix(in srgb, currentColor 10%, transparent);
  opacity: 1;
}

.ui-chip__remove:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

.ui-chip__remove .material-symbols-outlined {
  font-size: 14px;
}
</style>

```

## Dropdown

- File: `apps/desktop/src/components/ui/Dropdown/Dropdown.vue`
- Description: 统一下拉选择控件。
- Key props: 以源码中的 `defineProps` 为准。

```vue
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
  font: var(--font-caption);
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

```

## Input

- File: `apps/desktop/src/components/ui/Input/Input.vue`
- Description: 统一输入控件，支持错误、禁用和辅助反馈。
- Key props: 以源码中的 `defineProps` 为准。

```vue
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

```

## Modal

- File: `apps/desktop/src/components/ui/Modal/Modal.vue`
- Description: 统一模态与高风险确认容器。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div
        v-if="open"
        class="ui-modal-backdrop"
        :data-theme="theme"
        aria-hidden="true"
        @click="handleBackdropClick"
        @keydown.esc="handleEscKey"
      >
        <div
          ref="modalRef"
          class="ui-modal"
          :class="`ui-modal--${size}`"
          role="dialog"
          aria-modal="true"
          @click.stop
        >
          <header v-if="$slots.header || title" class="ui-modal__header">
            <slot name="header">
              <h2 class="ui-modal__title">{{ title }}</h2>
            </slot>
            <button
              v-if="closable"
              class="ui-modal__close"
              aria-label="关闭弹窗"
              @click="emit('close')"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </header>

          <main class="ui-modal__body">
            <slot />
          </main>

          <footer v-if="$slots.footer" class="ui-modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useShellUiStore } from "@/stores/shell-ui";

const props = defineProps<{
  closable?: boolean;
  closeOnBackdrop?: boolean;
  open: boolean;
  size?: "sm" | "md" | "lg" | "fullscreen";
  title?: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const shellUiStore = useShellUiStore();
const theme = computed(() => shellUiStore.theme);
const modalRef = ref<HTMLElement | null>(null);

/* 记录打开前的焦点元素，关闭时恢复 */
let previousActiveElement: HTMLElement | null = null;

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      previousActiveElement = document.activeElement as HTMLElement | null;
      nextTick(() => {
        /* 聚焦到 Modal 内第一个可聚焦元素，或 Modal 本身 */
        const firstFocusable = modalRef.value?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        (firstFocusable || modalRef.value)?.focus();
      });
    } else {
      previousActiveElement?.focus();
      previousActiveElement = null;
    }
  }
);

function handleBackdropClick() {
  if (props.closeOnBackdrop && props.closable) {
    emit("close");
  }
}

function handleEscKey() {
  if (props.closable) {
    emit("close");
  }
}
</script>

<style scoped>
.ui-modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-bg-overlay);
  z-index: var(--z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
  backdrop-filter: blur(8px);
}

.ui-modal {
  background: var(--color-bg-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border-subtle);
  display: flex;
  flex-direction: column;
  max-height: 100%;
  width: 100%;
  color: var(--color-text-primary);
  position: relative;
  z-index: var(--z-modal);
}

.ui-modal--sm { max-width: 400px; }
.ui-modal--md { max-width: 640px; }
.ui-modal--lg { max-width: 960px; }
.ui-modal--fullscreen {
  max-width: 100%;
  height: 100%;
  border-radius: 0;
  border: none;
}

.ui-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border-subtle);
  flex-shrink: 0;
}

.ui-modal__title {
  margin: 0;
  font: var(--font-title-lg);
  letter-spacing: var(--ls-title-lg);
  color: var(--color-text-primary);
}

.ui-modal__close {
  background: transparent;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  margin-right: -8px;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.ui-modal__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.ui-modal__close:focus-visible {
  outline: 2px solid var(--color-brand-primary);
  outline-offset: 2px;
}

.ui-modal__body {
  padding: var(--space-6);
  overflow-y: auto;
  flex: 1;
}

.ui-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  flex-shrink: 0;
}

.ui-modal--fullscreen .ui-modal__footer {
  border-radius: 0;
}

/* Modal Entry Animation */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard);
}

.modal-fade-enter-active .ui-modal,
.modal-fade-leave-active .ui-modal {
  transition: transform var(--motion-slow) var(--ease-spring);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .ui-modal,
.modal-fade-leave-to .ui-modal {
  transform: translateY(16px) scale(0.96);
}

@media (max-width: 640px) {
  .ui-modal-backdrop {
    padding: var(--space-4);
  }
}
</style>

```

## Progress

- File: `apps/desktop/src/components/ui/Progress/Progress.vue`
- Description: 统一确定型与任务进度反馈。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div
    class="ui-progress"
    :class="{ 'is-indeterminate': indeterminate }"
    :aria-valuemax="max"
    :aria-valuemin="0"
    :aria-valuenow="clampedValue"
    role="progressbar"
  >
    <div class="ui-progress__track">
      <div class="ui-progress__fill" :style="{ width: indeterminate ? undefined : `${fillWidth}%` }" />
    </div>
    <span v-if="showLabel" class="ui-progress__label">{{ indeterminate ? "处理中" : `${Math.round(fillWidth)}%` }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    indeterminate?: boolean;
    max?: number;
    showLabel?: boolean;
    value?: number;
  }>(),
  {
    indeterminate: false,
    max: 100,
    showLabel: false,
    value: 0
  }
);

const clampedValue = computed(() => Math.min(Math.max(props.value, 0), props.max));
const fillWidth = computed(() => (props.max <= 0 ? 0 : (clampedValue.value / props.max) * 100));
</script>

<style scoped>
.ui-progress {
  animation: progress-enter var(--motion-content) var(--ease-standard);
  display: grid;
  gap: 6px;
}

@keyframes progress-enter {
  from { opacity: 0; }
  to { opacity: 1; }
}

.ui-progress__track {
  background: var(--color-bg-muted);
  border-radius: var(--radius-full);
  height: 8px;
  overflow: hidden;
}

.ui-progress__fill {
  background: var(--gradient-ai-primary);
  background-size: 160px 100%;
  border-radius: inherit;
  height: 100%;
  transition: width var(--motion-default) var(--ease-standard);
}

.is-indeterminate .ui-progress__fill {
  animation: progress-flow var(--motion-pulse) linear infinite;
  width: 40%;
}

.ui-progress__label {
  color: var(--color-text-secondary);
  font: var(--font-caption);
}
</style>

```

## Skeleton

- File: `apps/desktop/src/components/ui/Skeleton/Skeleton.vue`
- Description: 统一加载骨架。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div
    class="ui-skeleton"
    :class="[`ui-skeleton--${variant}`, `ui-skeleton--${width}`, `ui-skeleton--${height}`]"
    :style="customStyle"
    :aria-busy="true"
    aria-live="polite"
  >
    <span class="sr-only">加载中</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    variant?: "text" | "circle" | "rect" | "card";
    width?: "full" | "3/4" | "1/2" | "1/3" | "1/4" | "auto";
    height?: "sm" | "md" | "lg" | "auto";
    customWidth?: string;
    customHeight?: string;
  }>(),
  {
    variant: "text",
    width: "full",
    height: "sm",
    customWidth: undefined,
    customHeight: undefined
  }
);

const customStyle = computed(() => {
  const style: Record<string, string> = {};
  if (props.customWidth) style.width = props.customWidth;
  if (props.customHeight) style.height = props.customHeight;
  return style;
});
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.ui-skeleton {
  animation: skeleton-pulse var(--motion-pulse) ease-in-out infinite;
  background: var(--color-bg-muted);
  border-radius: var(--radius-sm);
  display: block;
  line-height: 1;
  min-height: 1em;
}

/* ── Variants ── */
.ui-skeleton--text {
  border-radius: var(--radius-xs);
  height: 1em;
}

.ui-skeleton--circle {
  border-radius: var(--radius-full);
  width: 40px;
  height: 40px;
}

.ui-skeleton--rect {
  border-radius: var(--radius-md);
  width: 100%;
  aspect-ratio: 16 / 9;
}

.ui-skeleton--card {
  border-radius: var(--radius-lg);
  width: 100%;
  height: 120px;
}

/* ── Width ── */
.ui-skeleton--full { width: 100%; }
.ui-skeleton--3\/4 { width: 75%; }
.ui-skeleton--1\/2 { width: 50%; }
.ui-skeleton--1\/3 { width: 33.33%; }
.ui-skeleton--1\/4 { width: 25%; }
.ui-skeleton--auto { width: auto; }

/* ── Height ── */
.ui-skeleton--sm { height: 1em; }
.ui-skeleton--md { height: 2em; }
.ui-skeleton--lg { height: 3em; }
.ui-skeleton--auto { height: auto; }
</style>

```

## Tab

- File: `apps/desktop/src/components/ui/Tab/Tab.vue`
- Description: 统一页内切换标签。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div class="ui-tabs">
    <div
      class="ui-tabs__list"
      role="tablist"
      :aria-label="ariaLabel"
      ref="tabListRef"
    >
      <button
        v-for="(tab, index) in tabs"
        :key="tab.value"
        class="ui-tabs__tab"
        :class="{ 'is-active': modelValue === tab.value }"
        role="tab"
        :aria-selected="modelValue === tab.value"
        :aria-controls="`tabpanel-${tab.value}`"
        :id="`tab-${tab.value}`"
        :tabindex="modelValue === tab.value ? 0 : -1"
        @click="selectTab(tab.value, index)"
        @keydown="handleKeydown($event, index)"
        ref="tabRefs"
      >
        <span v-if="tab.icon" class="ui-tabs__icon material-symbols-outlined">{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
        <span v-if="tab.badge" class="ui-tabs__badge">{{ tab.badge }}</span>
      </button>

      <!-- Sliding Indicator -->
      <div class="ui-tabs__indicator" :style="indicatorStyle"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

export type TabItem = {
  label: string;
  value: string;
  icon?: string;
  badge?: string | number;
};

const props = defineProps<{
  ariaLabel?: string;
  modelValue: string;
  tabs: TabItem[];
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
  (e: "change", value: string): void;
}>();

const tabListRef = ref<HTMLElement | null>(null);
const tabRefs = ref<HTMLElement[]>([]);

const indicatorStyle = ref({
  transform: "translateX(0)",
  width: "0px"
});

function selectTab(value: string, index: number) {
  emit("update:modelValue", value);
  emit("change", value);
  updateIndicator(index);
}

function handleKeydown(event: KeyboardEvent, currentIndex: number) {
  let nextIndex = currentIndex;
  if (event.key === "ArrowRight") {
    nextIndex = (currentIndex + 1) % props.tabs.length;
  } else if (event.key === "ArrowLeft") {
    nextIndex = (currentIndex - 1 + props.tabs.length) % props.tabs.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = props.tabs.length - 1;
  } else {
    return;
  }

  event.preventDefault();
  const nextTab = props.tabs[nextIndex];
  selectTab(nextTab.value, nextIndex);
  tabRefs.value[nextIndex]?.focus();
}

function updateIndicator(index: number) {
  nextTick(() => {
    const tabEl = tabRefs.value[index];
    if (tabEl && tabListRef.value) {
      const listRect = tabListRef.value.getBoundingClientRect();
      const tabRect = tabEl.getBoundingClientRect();
      
      const left = tabRect.left - listRect.left + tabListRef.value.scrollLeft;
      indicatorStyle.value = {
        transform: `translateX(${left}px)`,
        width: `${tabRect.width}px`
      };
    }
  });
}

// Watch for external value changes and window resize to update indicator
watch(
  () => props.modelValue,
  (newVal) => {
    const index = props.tabs.findIndex((t) => t.value === newVal);
    if (index !== -1) {
      updateIndicator(index);
    }
  },
  { immediate: true }
);

// 监听容器尺寸变化，重新计算 indicator 位置
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (tabListRef.value) {
    resizeObserver = new ResizeObserver(() => {
      const index = props.tabs.findIndex((t) => t.value === props.modelValue);
      if (index !== -1) {
        updateIndicator(index);
      }
    });
    resizeObserver.observe(tabListRef.value);
  }
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
});
</script>

<style scoped>
.ui-tabs {
  width: 100%;
}

.ui-tabs__list {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--color-border-subtle);
  position: relative;
  overflow-x: auto;
  scrollbar-width: none; /* Firefox */
}

.ui-tabs__list::-webkit-scrollbar {
  display: none; /* Chrome, Safari */
}

.ui-tabs__tab {
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 48px;
  padding: 0 var(--space-4);
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  position: relative;
  white-space: nowrap;
  transition: color var(--motion-fast) var(--ease-standard);
  outline: none;
}

.ui-tabs__tab:hover {
  color: var(--color-text-primary);
}

.ui-tabs__tab.is-active {
  color: var(--color-brand-primary);
}

.ui-tabs__tab:focus-visible {
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.ui-tabs__icon {
  font-size: 18px;
}

.ui-tabs__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 20px;
  min-width: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font: var(--font-caption);
  font-weight: 700;
}

.ui-tabs__tab.is-active .ui-tabs__badge {
  background: color-mix(in srgb, var(--color-brand-primary) 12%, transparent);
  color: var(--color-brand-primary);
}

.ui-tabs__indicator {
  position: absolute;
  bottom: -1px;
  left: 0;
  height: 2px;
  background: var(--color-brand-primary);
  border-radius: 2px 2px 0 0;
  transition:
    transform var(--motion-default) var(--ease-spring),
    width var(--motion-default) var(--ease-spring);
  pointer-events: none;
}
</style>

```

## ToastContainer

- File: `apps/desktop/src/components/ui/Toast/Toast.vue`
- Description: 单条全局轻反馈。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div class="ui-toast" :class="[`ui-toast--${tone}`]" role="status" v-bind="$attrs">
    <span class="material-symbols-outlined ui-toast__icon">{{ icon }}</span>
    <div class="ui-toast__body">
      <strong v-if="title">{{ title }}</strong>
      <span><slot /></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    title?: string;
    tone?: "info" | "success" | "warning" | "danger";
  }>(),
  {
    title: "",
    tone: "info"
  }
);

const icon = computed(() => {
  switch (props.tone) {
    case "success":
      return "check_circle";
    case "warning":
      return "warning";
    case "danger":
      return "error";
    default:
      return "info";
  }
});
</script>

<style scoped>
.ui-toast {
  align-items: flex-start;
  animation: toast-slide-up var(--motion-default) var(--ease-spring);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: auto minmax(0, 1fr);
  padding: var(--space-3) var(--space-4);
}

.ui-toast__icon {
  font-size: 18px;
  line-height: 1.2;
}

.ui-toast__body {
  display: grid;
  gap: 4px;
}

.ui-toast__body strong {
  font: var(--font-body-sm);
}

.ui-toast__body span {
  color: var(--color-text-secondary);
  font: var(--font-caption);
}

.ui-toast--info {
  background: color-mix(in srgb, var(--color-info) 10%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-info) 28%, var(--color-border-default));
}

.ui-toast--info .ui-toast__icon,
.ui-toast--info strong {
  color: var(--color-info);
}

.ui-toast--success {
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border-default));
}

.ui-toast--success .ui-toast__icon,
.ui-toast--success strong {
  color: var(--color-success);
}

.ui-toast--warning {
  background: color-mix(in srgb, var(--color-warning) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-warning) 28%, var(--color-border-default));
}

.ui-toast--warning .ui-toast__icon,
.ui-toast--warning strong {
  color: var(--color-warning);
}

.ui-toast--danger {
  background: color-mix(in srgb, var(--color-danger) 12%, var(--color-bg-elevated));
  border-color: color-mix(in srgb, var(--color-danger) 28%, var(--color-border-default));
}

.ui-toast--danger .ui-toast__icon,
.ui-toast--danger strong {
  color: var(--color-danger);
}
</style>

```

## Toast

- File: `apps/desktop/src/components/ui/Toast/ToastContainer.vue`
- Description: 单条全局轻反馈。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast-slide"
      tag="div"
      class="toast-container"
      v-if="toast.items.length"
    >
      <div
        v-for="item in toast.items"
        :key="item.id"
        class="toast-wrapper"
        @click="toast.dismiss(item.id)"
      >
        <Toast :title="item.title" :tone="item.tone">{{ item.message }}</Toast>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import Toast from "./Toast.vue";
import { useToast } from "@/composables/useToast";

const toast = useToast();
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 400px;
  pointer-events: none;
}

.toast-wrapper {
  pointer-events: auto;
  cursor: pointer;
}

.toast-slide-enter-active {
  transition: all var(--motion-default) var(--ease-spring);
}

.toast-slide-leave-active {
  transition: all var(--motion-fast) var(--ease-standard);
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(60px);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(60px) scale(0.95);
}

.toast-slide-move {
  transition: transform var(--motion-instant) var(--ease-standard);
}
</style>

```

## TkopsBrandMark

- File: `apps/desktop/src/components/brand/TkopsBrandMark.vue`
- Description: 真实 TK-OPS 品牌标记，供 Title Bar 与 Sidebar 复用。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <span class="tkops-brand-mark" :class="`tkops-brand-mark--${size}`" aria-label="TK-OPS" role="img">
    <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect class="tkops-brand-mark__plate" x="3" y="3" width="26" height="26" rx="7" />
      <path class="tkops-brand-mark__frame" d="M9 10h8.25c3.7 0 6.75 2.85 6.75 6.45S20.95 23 17.25 23H9z" />
      <path class="tkops-brand-mark__cut" d="M13 10v13" />
      <path class="tkops-brand-mark__signal" d="M17 13.1 21.6 16 17 18.9z" />
      <circle class="tkops-brand-mark__node" cx="9" cy="10" r="1.45" />
      <circle class="tkops-brand-mark__node" cx="9" cy="23" r="1.45" />
    </svg>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: "sm" | "md";
  }>(),
  {
    size: "sm"
  }
);
</script>

<style scoped>
.tkops-brand-mark {
  display: inline-flex;
  flex: 0 0 auto;
  height: 20px;
  width: 20px;
}

.tkops-brand-mark--md {
  height: 32px;
  width: 32px;
}

.tkops-brand-mark svg {
  display: block;
  height: 100%;
  overflow: visible;
  width: 100%;
}

.tkops-brand-mark__plate {
  fill: color-mix(in srgb, var(--color-bg-elevated) 88%, var(--color-brand-primary));
  stroke: color-mix(in srgb, var(--color-brand-primary) 64%, var(--color-border-strong));
  stroke-width: 1.4;
}

.tkops-brand-mark__frame {
  fill: color-mix(in srgb, var(--color-brand-primary) 20%, transparent);
  stroke: var(--color-brand-primary);
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.tkops-brand-mark__cut {
  fill: none;
  stroke: color-mix(in srgb, var(--color-text-primary) 72%, var(--color-brand-primary));
  stroke-linecap: round;
  stroke-width: 1.7;
}

.tkops-brand-mark__signal {
  fill: var(--color-brand-secondary);
}

.tkops-brand-mark__node {
  fill: var(--color-brand-primary);
}
</style>

```

## ProjectContextGuard

- File: `apps/desktop/src/components/common/ProjectContextGuard.vue`
- Description: 项目上下文缺失时的统一引导门禁。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div class="project-context-guard">
    <template v-if="projectStore.currentProject">
      <slot />
    </template>
    <div v-else class="guard-overlay">
      <EmptyState
        icon="folder_off"
        title="需要选择项目"
        :description="`你当前正在访问「${routeTitle}」，该功能需要绑定一个具体的创作项目。请先创建新项目或从总览中打开现有项目。`"
        action-label="前往创作总览"
        @action="navigateToDashboard"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useProjectStore } from '@/stores/project';
import EmptyState from './EmptyState.vue';

const projectStore = useProjectStore();
const router = useRouter();
const route = useRoute();

const routeTitle = computed(() => (route.meta.title as string) || '当前页面');

function navigateToDashboard() {
  router.push('/dashboard');
}
</script>

<style scoped>
.project-context-guard {
  height: 100%;
  width: 100%;
}

.guard-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 500px;
}
</style>

```

## EmptyState

- File: `apps/desktop/src/components/common/EmptyState.vue`
- Description: 统一中性空态 / 警告态 / 错误态与下一步动作。
- Key props: 以源码中的 `defineProps` 为准。

```vue
<template>
  <div class="empty-state-container" :class="`empty-state--${type}`">
    <div class="empty-state__visual">
      <div class="floating-orb">
        <span class="material-symbols-outlined">{{ icon }}</span>
      </div>
      <div class="glow-shadow"></div>
    </div>

    <div class="empty-state__content">
      <h2 class="empty-state__title">{{ title }}</h2>
      <p class="empty-state__description">{{ description }}</p>

      <div class="empty-state__actions">
        <slot name="actions">
          <button
            v-if="actionLabel"
            class="settings-page__button"
            @click="$emit('action')"
          >
            {{ actionLabel }}
          </button>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  icon?: string;
  title: string;
  description: string;
  actionLabel?: string;
  type?: 'info' | 'warning' | 'error';
}

withDefaults(defineProps<Props>(), {
  icon: 'database',
  type: 'info'
});

defineEmits(['action']);
</script>

<style scoped>
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
  min-height: 400px;
  width: 100%;
}

.empty-state__visual {
  position: relative;
  margin-bottom: 32px;
  perspective: 1000px;
}

.floating-orb {
  width: 100px;
  height: 100px;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: var(--brand-primary);
  box-shadow: var(--shadow-md);
  animation: float 6s ease-in-out infinite;
  transform-style: preserve-3d;
}

.floating-orb .material-symbols-outlined {
  font-size: 56px;
  filter: drop-shadow(0 0 10px rgba(0, 242, 234, 0.3));
}

.glow-shadow {
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 10px;
  background: rgba(0, 0, 0, 0.1);
  filter: blur(8px);
  border-radius: 50%;
  animation: shadow-scale 6s ease-in-out infinite;
}

.empty-state__content {
  max-width: 480px;
}

.empty-state__title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}

.empty-state__description {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0 0 32px;
}

.empty-state__actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotateX(5deg) rotateY(5deg);
  }
  50% {
    transform: translateY(-20px) rotateX(-5deg) rotateY(-10deg);
  }
}

@keyframes shadow-scale {
  0%, 100% {
    transform: translateX(-50%) scale(1);
    opacity: 0.2;
  }
  50% {
    transform: translateX(-50%) scale(0.7);
    opacity: 0.1;
  }
}

/* Theme specifics */
:root[data-theme="dark"] .floating-orb {
  background: var(--surface-secondary);
  border-color: var(--border-strong);
}

:root[data-theme="dark"] .glow-shadow {
  background: rgba(0, 242, 234, 0.15);
}
</style>

```
