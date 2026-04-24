<template>
  <section class="dashboard-hero" data-dashboard-section="hero" :data-dashboard-state="state">
    <div class="dashboard-hero__inner">
      <div class="dashboard-hero__content">
        <div class="dashboard-hero__greeting">
          {{ timeGreeting }}，创作者
        </div>
        <h2 class="dashboard-hero__title">
          {{ title }}
        </h2>
        <p class="dashboard-hero__desc">
          {{ summary }}
        </p>
      </div>

      <div class="dashboard-hero__actions">
        <Button
          v-if="hasProjects"
          variant="secondary"
          size="lg"
          @click="emit('action', 'view-all')"
        >
          查看全部项目
        </Button>
        <Button
          variant="ai"
          size="lg"
          :running="state === 'loading'"
          @click="emit('action', 'primary')"
        >
          <template #leading>
            <span class="material-symbols-outlined">
              {{ primaryActionIcon }}
            </span>
          </template>
          {{ primaryActionLabel }}
        </Button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import Button from "@/components/ui/Button/Button.vue";

const props = defineProps<{
  hasProjects: boolean;
  primaryActionLabel: string;
  primaryActionIcon: string;
  state: "loading" | "ready" | "empty" | "error" | "blocked";
  summary: string;
  title: string;
}>();

const emit = defineEmits<{
  (e: "action", type: "primary" | "view-all"): void;
}>();

const timeGreeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 12) return "上午好";
  if (hour < 14) return "中午好";
  if (hour < 18) return "下午好";
  return "晚上好";
});
</script>

<style scoped>
.dashboard-hero {
  border-radius: var(--radius-xl);
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
  /* Fallback color for the orb if gradient fails */
  background-color: var(--color-bg-surface);
}

.dashboard-hero::after {
  content: '';
  position: absolute;
  top: -40%;
  right: -10%;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: var(--gradient-aurora);
  filter: blur(60px);
  opacity: 0.8;
  animation: aurora-rotate 20s linear infinite;
  pointer-events: none;
  z-index: 0;
  /* Make sure the orb colors are solid to contrast with white backgrounds */
  mix-blend-mode: multiply;
}

@media (prefers-color-scheme: dark) {
  .dashboard-hero::after {
    mix-blend-mode: screen;
    opacity: 0.4;
  }
}

.dashboard-hero__inner {
  position: relative;
  z-index: 1;
  padding: var(--space-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  background: transparent;
  min-height: 240px;
}

.dashboard-hero__content {
  flex: 1;
  min-width: 0;
}

.dashboard-hero__greeting {
  font: var(--font-title-sm);
  letter-spacing: var(--ls-title-sm);
  color: var(--color-brand-primary);
  margin-bottom: var(--space-3);
  text-transform: uppercase;
}

.dashboard-hero__title {
  font: var(--font-display-lg);
  letter-spacing: var(--ls-display-lg);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3) 0;
  line-height: 1.2;
}

.dashboard-hero__desc {
  font: var(--font-body-lg);
  letter-spacing: var(--ls-body-lg);
  color: var(--color-text-secondary);
  max-width: 640px;
  margin: 0;
  line-height: 1.6;
}

.dashboard-hero__actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

@media (max-width: 960px) {
  .dashboard-hero__inner {
    flex-direction: column;
    align-items: flex-start;
    padding: var(--space-6);
  }
}
</style>
