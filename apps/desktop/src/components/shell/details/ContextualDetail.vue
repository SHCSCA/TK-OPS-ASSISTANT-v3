<template>
  <div class="contextual-detail">
    <section class="detail-section">
      <p class="detail-section__title">创作上下文</p>
      <div class="info-well">
        <p>当前页面：{{ routeTitle }}</p>
        <p v-if="projectStore.currentProject">绑定项目：{{ projectStore.currentProject.projectName }}</p>
      </div>
    </section>
    
    <section class="detail-section">
      <p class="detail-section__title">AI 辅助建议</p>
      <div class="ai-suggestion-box">
        <span class="material-symbols-outlined">auto_awesome</span>
        <p>正在分析当前创作状态，稍后将为您提供智能建议...</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useProjectStore } from '@/stores/project';

const route = useRoute();
const projectStore = useProjectStore();
const routeTitle = computed(() => (route.meta.title as string) || '创作工作台');
</script>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--border-default);
  padding: 16px 0;
}

.detail-section__title {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.05em;
  margin: 0 0 12px;
  text-transform: uppercase;
}

.info-well {
  background: var(--surface-tertiary);
  padding: 12px;
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-secondary);
}

.ai-suggestion-box {
  background: color-mix(in srgb, var(--brand-primary) 5%, transparent);
  border: 1px dashed color-mix(in srgb, var(--brand-primary) 20%, transparent);
  padding: 16px;
  border-radius: var(--radius-md);
  text-align: center;
  color: var(--text-secondary);
}

.ai-suggestion-box .material-symbols-outlined {
  color: var(--brand-primary);
  font-size: 32px;
  margin-bottom: 8px;
}
</style>
