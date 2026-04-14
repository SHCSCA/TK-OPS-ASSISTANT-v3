<template>
  <section class="chain-rail-panel" data-dashboard-section="chain-rail">
    <div class="chain-rail-panel__header">
      <div>
        <p class="chain-rail-panel__label">创作链路</p>
        <h4 class="chain-rail-panel__title">{{ hasProject ? '下一步动作' : '等待项目上下文' }}</h4>
      </div>
    </div>

    <div class="chain-rail-steps">
      <RouterLink v-for="step in steps" :key="step.path" class="chain-step" :to="step.path">
        <span class="chain-step__index">{{ step.index }}</span>
        <div class="chain-step__body">
          <strong>{{ step.title }}</strong>
          <p>{{ step.summary }}</p>
        </div>
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

defineProps<{
  hasProject: boolean;
  steps: Array<{
    index: string;
    path: string;
    summary: string;
    title: string;
  }>;
}>();
</script>
