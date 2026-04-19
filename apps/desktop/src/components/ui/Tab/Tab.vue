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
import { computed, nextTick, ref, watch } from "vue";

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

// Optional: you could add a ResizeObserver here in a real production environment
// to re-calculate the indicator if the container width changes.
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
