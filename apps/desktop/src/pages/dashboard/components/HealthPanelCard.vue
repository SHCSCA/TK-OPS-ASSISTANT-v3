<template>
  <Card class="health-card">
    <div class="health-card__header">
      <span class="health-card__label">{{ label }}</span>
      <Chip v-if="statusLabel" :variant="statusTone" size="sm" class="health-card__badge">
        {{ statusLabel }}
      </Chip>
    </div>

    <div class="health-card__body">
      <div class="health-card__number-wrap">
        <span class="health-card__number">{{ displayValue }}</span>
        <span v-if="unit" class="health-card__unit">{{ unit }}</span>
      </div>
      <div v-if="$slots.sparkline" class="health-card__sparkline">
        <slot name="sparkline" />
      </div>
    </div>

    <div v-if="trendLabel" class="health-card__footer">
      <span
        class="material-symbols-outlined"
        :class="{
          'trend-up': trend === 'up',
          'trend-down': trend === 'down'
        }"
      >
        {{ trend === "up" ? "trending_up" : trend === "down" ? "trending_down" : "trending_flat" }}
      </span>
      {{ trendLabel }}
    </div>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from "vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const props = defineProps<{
  label: string;
  status?: "healthy" | "warning" | "error" | "offline";
  statusLabel?: string;
  numericValue: number;
  unit?: string;
  trend?: "up" | "down" | "flat";
  trendLabel?: string;
}>();

const statusTone = computed(() => {
  switch (props.status) {
    case "healthy": return "success";
    case "warning": return "warning";
    case "error":
    case "offline": return "danger";
    default: return "default";
  }
});

const displayValue = ref(0);

function animateValue(start: number, end: number, duration: number) {
  let startTimestamp: number | null = null;
  const step = (timestamp: number) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const easeProgress = 1 - Math.pow(1 - progress, 3); // cubic ease-out
    displayValue.value = Math.floor(easeProgress * (end - start) + start);
    if (progress < 1) {
      window.requestAnimationFrame(step);
    } else {
      displayValue.value = end;
    }
  };
  window.requestAnimationFrame(step);
}

watch(() => props.numericValue, (newVal) => {
  animateValue(displayValue.value, newVal, 1000);
});

onMounted(() => {
  animateValue(0, props.numericValue, 1000);
});
</script>

<style scoped>
.health-card {
  display: flex;
  flex-direction: column;
  height: 160px;
  padding: var(--space-4);
}

.health-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: auto;
}

.health-card__label {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-secondary);
  text-transform: uppercase;
}

.health-card__body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.health-card__number-wrap {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.health-card__number {
  font: var(--font-numeric-lg);
  letter-spacing: var(--ls-numeric-lg);
  color: var(--color-text-primary);
  line-height: 1;
}

.health-card__unit {
  font: var(--font-body-sm);
  letter-spacing: var(--ls-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.health-card__sparkline {
  flex: 1;
  height: 32px;
  min-width: 64px;
}

.health-card__footer {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-3);
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
}

.health-card__footer .material-symbols-outlined {
  font-size: 14px;
}

.trend-up {
  color: var(--color-danger);
}

.trend-down {
  color: var(--color-success);
}
</style>
