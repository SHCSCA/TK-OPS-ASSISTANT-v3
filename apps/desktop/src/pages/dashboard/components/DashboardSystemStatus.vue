<template>
  <section class="command-panel system-card" data-dashboard-section="system-status">
    <p class="detail-panel__label">运行与授权</p>
    <div class="dashboard-metric">
      <span>Runtime</span>
      <strong>{{ runtimeLabel }}</strong>
    </div>
    <div class="dashboard-metric">
      <span>许可证</span>
      <strong>{{ licenseLabel }}</strong>
    </div>
    <div class="dashboard-metric">
      <span>配置状态</span>
      <strong>{{ configStatusLabel }}</strong>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  configStatusLabel: string;
  licenseLabel: string;
  runtimeLabel: string;
}>();
</script>
