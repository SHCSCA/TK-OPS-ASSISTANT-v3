<template>
  <section class="command-panel system-card" data-dashboard-section="ai-defaults">
    <p class="detail-panel__label">AI 默认项</p>
    <div class="dashboard-metric">
      <span>Provider</span>
      <strong>{{ provider }}</strong>
    </div>
    <div class="dashboard-metric">
      <span>模型</span>
      <strong>{{ model }}</strong>
    </div>
    <div class="dashboard-metric">
      <span>工作目录</span>
      <strong>{{ workspaceRoot }}</strong>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  model: string;
  provider: string;
  workspaceRoot: string;
}>();
</script>
