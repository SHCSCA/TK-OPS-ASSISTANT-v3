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
