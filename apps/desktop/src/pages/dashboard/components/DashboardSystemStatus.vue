<template>
  <section class="system-status-panel" data-dashboard-section="system-status">
    <div class="system-status-panel__header">
      <h4 class="system-status-panel__title">系统状态</h4>
      <span class="live-badge">
        <span class="live-badge__dot"></span>
        <span class="live-badge__text">Live</span>
      </span>
    </div>

    <div class="system-status-list">
      <div class="system-status-row">
        <div class="system-status-row__info">
          <p class="system-status-row__name">Runtime 引擎</p>
          <p class="system-status-row__sub">{{ runtimeLabel }}</p>
        </div>
        <p class="system-status-row__state" :class="runtimeLabel.includes('在线') ? 'system-status-row__state--active' : 'system-status-row__state--inactive'">
          {{ runtimeLabel.includes('在线') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="system-status-row">
        <div class="system-status-row__info">
          <p class="system-status-row__name">许可证授权</p>
          <p class="system-status-row__sub">{{ licenseLabel }}</p>
        </div>
        <p class="system-status-row__state" :class="licenseLabel.includes('已激活') ? 'system-status-row__state--active' : 'system-status-row__state--inactive'">
          {{ licenseLabel.includes('已激活') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="system-status-row">
        <div class="system-status-row__info">
          <p class="system-status-row__name">配置总线</p>
          <p class="system-status-row__sub">{{ configStatusLabel }}</p>
        </div>
        <p class="system-status-row__state" :class="configStatusLabel.includes('就绪') ? 'system-status-row__state--active' : 'system-status-row__state--inactive'">
          {{ configStatusLabel.includes('就绪') ? 'Active' : 'Inactive' }}
        </p>
      </div>
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
