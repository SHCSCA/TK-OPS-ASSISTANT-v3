<template>
  <aside class="shell-detail-panel">
    <section class="detail-section">
      <div class="detail-section__header">
        <p class="detail-section__title">系统状态</p>
        <span class="live-indicator">
          <span class="live-indicator__dot"></span>
          <span class="live-indicator__text">Live</span>
        </span>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">Runtime 引擎</p>
          <p class="status-row__sub">{{ runtimeVersion }}</p>
        </div>
        <p class="status-row__value" :class="runtimeLabel.includes('在线') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ runtimeLabel.includes('在线') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">许可证授权</p>
          <p class="status-row__sub">{{ maskedCode }}</p>
        </div>
        <p class="status-row__value" :class="licenseLabel.includes('已激活') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ licenseLabel.includes('已激活') ? 'Active' : 'Inactive' }}
        </p>
      </div>

      <div class="status-row">
        <div class="status-row__info">
          <p class="status-row__label">配置总线</p>
          <p class="status-row__sub">{{ configStatusLabel }}</p>
        </div>
        <p class="status-row__value" :class="configStatusLabel.includes('就绪') ? 'status-row__value--active' : 'status-row__value--inactive'">
          {{ configStatusLabel.includes('就绪') ? 'Active' : 'Inactive' }}
        </p>
      </div>
    </section>

    <section class="detail-section">
      <p class="detail-section__title">项目上下文</p>
      <template v-if="projectName">
        <div class="project-context">
          <strong>{{ projectName }}</strong>
          <p>状态：{{ projectStatus }}</p>
        </div>
      </template>
      <p v-else class="detail-section__empty">尚未选择项目。需要项目上下文的页面会先回到创作总览。</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  configStatusLabel: string;
  licenseLabel: string;
  maskedCode: string;
  projectName: string;
  projectStatus: string;
  runtimeLabel: string;
  runtimeVersion: string;
}>();
</script>
