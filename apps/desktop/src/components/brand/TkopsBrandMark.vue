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
