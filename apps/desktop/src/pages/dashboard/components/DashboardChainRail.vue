<template>
  <section class="command-panel command-panel--wide chain-card" data-dashboard-section="chain-rail">
    <div class="command-panel__title-row">
      <div>
        <p class="detail-panel__label">创作链路</p>
        <h2>{{ hasProject ? "下一步动作" : "等待项目上下文" }}</h2>
      </div>
      <span class="page-chip page-chip--muted">Project -> Script -> Storyboard -> Timeline</span>
    </div>

    <div class="chain-rail chain-rail--command">
      <RouterLink v-for="step in steps" :key="step.path" class="chain-step" :to="step.path">
        <span>{{ step.index }}</span>
        <strong>{{ step.title }}</strong>
        <p>{{ step.summary }}</p>
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
